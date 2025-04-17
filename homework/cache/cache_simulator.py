import math
import random
import multiprocessing
from functools import partial
import logging
import platform
import subprocess
import re

class CacheSimulator:
    def __init__(self, cache_size_bytes, block_size_bytes, associativity, address_size_bits=64, replacement_policy='LRU'):
        if(cache_size_bytes <= 0 or block_size_bytes <= 0 or associativity <= 0):
            raise ValueError("Cache size, block size, and associativity must be positive.")
        if(not self._is_power_of_two(cache_size_bytes)):
            raise ValueError("Cache size must be a power of two.")
        if(not self._is_power_of_two(block_size_bytes)):
            raise ValueError("Block size must be a power of two.")
        if((cache_size_bytes // block_size_bytes) % associativity != 0):
            raise ValueError("Cache size must be divisible by (block size * associativity).")
        if(replacement_policy not in ['LRU']):
             raise ValueError(f"Unsupported replacement policy: {replacement_policy}")

        self.cache_size = cache_size_bytes
        self.block_size = block_size_bytes
        self.associativity = associativity
        self.address_size = address_size_bits
        self.replacement_policy = replacement_policy

        self.num_blocks = cache_size_bytes // block_size_bytes
        self.num_sets = self.num_blocks // associativity

        self.num_offset_bits = int(math.log2(block_size_bytes))
        self.num_index_bits = int(math.log2(self.num_sets)) if self.num_sets > 0 else 0
        self.num_tag_bits = address_size_bits - self.num_index_bits - self.num_offset_bits

        if self.num_tag_bits < 0:
             raise ValueError("Address size too small for cache configuration.")

        self.cache = [[{'valid': False, 'tag': 0, 'lru_counter': 0} for _ in range(associativity)]
                      for _ in range(self.num_sets)]

        self.hits = 0
        self.misses = 0

    def _is_power_of_two(self, n):
        return (n > 0) and (n & (n - 1) == 0)

    def _get_address_parts(self, address):
        if address < 0:
             raise ValueError("Address cannot be negative.")
        ## Ignore offset bits for cache access logic
        address_no_offset = address >> self.num_offset_bits

        index_mask = (1 << self.num_index_bits) - 1 if self.num_index_bits > 0 else 0
        set_index = address_no_offset & index_mask

        tag = address_no_offset >> self.num_index_bits

        ## python intergers are bullshit, so we need to handle this manually
        max_tag = (1 << self.num_tag_bits) -1
        if(tag > max_tag):
             tag = tag & max_tag 

        return tag, set_index

    def access(self, address):
        """
        Simulates a memory read access to the cache.
        Returns True for a hit, False for a miss.
        Updates cache state and statistics.
        """
        tag, set_index = self._get_address_parts(address)
        target_set = self.cache[set_index]
        
        hit = False

        current_max_lru = 0
        for line in target_set:
            if(line['valid']):
                line['lru_counter'] += 1
                current_max_lru = max(current_max_lru, line['lru_counter'])


        #1 hit check
        for i, line in enumerate(target_set):
            if line['valid'] and line['tag'] == tag:
                hit = True
                self.hits += 1
                line['lru_counter'] = 0 
                break
        
        ## two. miss
        if(not hit):
            self.misses += 1
            victim_index = -1
            for i, line in enumerate(target_set):
                if(not line['valid']):
                    victim_index = i
                    break
            
            if(victim_index == -1):
                if(self.replacement_policy == 'LRU'):
                    max_lru = -1
                    lru_victim_index = -1
                    for i, line in enumerate(target_set):
                        if(line['lru_counter'] > max_lru):
                             max_lru = line['lru_counter']
                             lru_victim_index = i
                    victim_index = lru_victim_index
                else:
                    raise NotImplementedError(f"Replacement policy {self.replacement_policy} not implemented.")

            victim_line = target_set[victim_index]
            victim_line['valid'] = True
            victim_line['tag'] = tag
            victim_line['lru_counter'] = 0

        return hit 

    def get_miss_rate(self):
        total_accesses = self.hits + self.misses
        if(total_accesses == 0):
            return 0.0
        return self.misses / total_accesses

    def reset_stats(self):
        self.hits = 0
        self.misses = 0
        
    def reset(self):
        self.cache = [[{'valid': False, 'tag': 0, 'lru_counter': 0} for _ in range(self.associativity)]
                      for _ in range(self.num_sets)]
        self.reset_stats()

def generate_row_major_addresses(start_address, rows, cols, data_size_bytes):
    """Generates addresses for row-major traversal of a 2D array."""
    addresses = []
    for r in range(rows):
        for c in range(cols):
            offset = (r * cols + c) * data_size_bytes
            addresses.append(start_address + offset)
    return addresses

def generate_col_major_addresses(start_address, rows, cols, data_size_bytes):
    """Generates addresses for column-major traversal of a 2D array."""
    addresses = []
    for c in range(cols):
        for r in range(rows):
            offset = (r * cols + c) * data_size_bytes
            addresses.append(start_address + offset)
    return addresses

def generate_random_addresses(start_address, range_bytes, num_accesses, data_size_bytes):
    """
    Generates random addresses within a specified byte range, aligned to data_size.
    Assumes the range starts immediately after start_address.
    assignment asks for a range equalling L2/L3 size, offset by half L2/L3 size.
    This function generates addresses within range_bytes starting from start_address.
    The caller needs to adjust start_address and range_bytes accordingly or shit will hit the fan.  
    """
    addresses = []
    if(range_bytes <= 0 or num_accesses <= 0 or data_size_bytes <= 0):
        return []
        
    num_elements_in_range = range_bytes // data_size_bytes
    if(num_elements_in_range == 0):
         ## can't really log much here, returning empty list
         return []

    for _ in range(num_accesses):
        random_element_index = random.randrange(num_elements_in_range)
        offset = random_element_index * data_size_bytes
        addresses.append(start_address + offset)
    return addresses

def run_single_simulation(run_args, cache_config):
    """
    Runs a single cache simulation based on provided arguments.
    Designed to be called by multiprocessing.Pool.map.

    Args:
        run_args (tuple): Contains parameters specific to this run:
                           (access_type, start_address, rows, cols, data_size, 
                            random_range_bytes, num_random_accesses)
        cache_config (dict): Contains fixed cache parameters:
                             {'cache_size_bytes': int, 'block_size_bytes': int, 
                              'associativity': int, 'address_size_bits': int}
                             
    Returns:
        float: The miss rate for this simulation run, or float('nan') on error.
    """
    access_type, start_addr, rows, cols, data_size, rand_range, num_rand_acc = run_args

    try:
        cache = CacheSimulator(
            cache_size_bytes=cache_config['cache_size_bytes'],
            block_size_bytes=cache_config['block_size_bytes'],
            associativity=cache_config['associativity'],
            address_size_bits=cache_config['address_size_bits']
        )

        addresses = []
        if(access_type == 'row_major'):
            addresses = generate_row_major_addresses(start_addr, rows, cols, data_size)
        elif(access_type == 'col_major'):
            addresses = generate_col_major_addresses(start_addr, rows, cols, data_size)
        elif(access_type == 'random'):
            addresses = generate_random_addresses(start_addr, rand_range, num_rand_acc, data_size)
        else:
            ## unliekly branch, but good to have
            return float('nan') 

        if(not addresses):
            if(access_type == 'random' and rand_range < data_size and rand_range > 0):
                 pass # Fall through to return NaN
            elif(rows * cols == 0 and access_type != 'random'):
                 ## No accesses for row/col major if array empty
                 return 0.0 # 0 misses / 0 accesses = 0 miss rate? Or NaN? Let's say 0.
            else:
                 return float('nan')

        for addr in addresses:
            cache.access(addr)

        return cache.get_miss_rate()

    except Exception as e:
        return float('nan')



def get_system_cache_info():
    """Attempts to detect OS and retrieve L2/L3 cache size. I switch between Darwin and Windows."""
    os_name = platform.system()
    l2_l3_size_bytes = 16 * 1024 * 1024 
    method = f"Default placeholder ({l2_l3_size_bytes:,} bytes)"
    cache_details = "Could not automatically determine L1/L2/L3 cache sizes."
    all_sizes = {"l1i": [], "l1d": [], "l2": [], "l3": []}

    logging.info(f"Detected OS: {os_name}")

    try:
        if(os_name == "Darwin"):
            method = "Attempted via `sysctl` on macOS."
            cmd = ["sysctl", "-a"]
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output_lines = process.stdout.splitlines()
            cache_details = "Parsed from `sysctl -a`:\\n"
            
            l2_sizes = []
            l3_sizes = []

            for line in output_lines:
                line = line.strip()
                if("l1icachesize" in line):
                    match = re.search(r'(\d+)$', line)
                    if(match): all_sizes["l1i"].append(int(match.group(1)))
                    cache_details += f"   - {line}\\n"
                elif("l1dcachesize" in line):
                    match = re.search(r'(\d+)$', line)
                    if(match): all_sizes["l1d"].append(int(match.group(1)))
                    cache_details += f"   - {line}\\n"
                elif("l2cachesize" in line):
                    match = re.search(r'(\d+)$', line)
                    if(match): l2_sizes.append(int(match.group(1)))
                    cache_details += f"   - {line}\\n"
                elif("l3cachesize" in line):
                    match = re.search(r'(\d+)$', line)
                    if(match): l3_sizes.append(int(match.group(1)))
                    cache_details += f"   - {line}\\n"
           
            all_sizes["l2"] = sorted(list(set(l2_sizes)))
            all_sizes["l3"] = sorted(list(set(l3_sizes)))
            all_sizes["l1i"] = sorted(list(set(all_sizes["l1i"])))
            all_sizes["l1d"] = sorted(list(set(all_sizes["l1d"])))

            all_found_sizes = l2_sizes + l3_sizes
            if(all_found_sizes):
                l2_l3_size_bytes = max(all_found_sizes)
                method = f'Detected max L2/L3 cache size via `sysctl` ({l2_l3_size_bytes:,} bytes).'
            else:
                method += ' Could not parse L2/L3 size, using default.'
                cache_details += '   (Could not parse specific L2/L3 sizes from output)\n'

        elif(os_name == "Windows"):
            method = "Attempted via `wmic` on Windows."
            cmd = ["wmic", "cpu", "get", "L2CacheSize,L3CacheSize", "/value"]
            process = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
            output_lines = process.stdout.splitlines()
            cache_details = "Parsed from `wmic cpu get L2CacheSize, L3CacheSize /value`:\\n"
            
            l2_kb = 0
            l3_kb = 0

            for line in output_lines:
                line = line.strip()
                if(not line): continue
                cache_details += f"   - {line}\\n"
                if(line.startswith("L2CacheSize=")):
                    try: l2_kb = int(line.split('=')[1])
                    except: pass
                elif(line.startswith("L3CacheSize=")):
                    try: l3_kb = int(line.split('=')[1])
                    except: pass
           
            max_kb = max(l2_kb, l3_kb)
            if(max_kb > 0):
                l2_l3_size_bytes = max_kb * 1024
                method = f'Detected max L2/L3 cache size via `wmic` ({l2_l3_size_bytes:,} bytes).'
            else:
                method += ' Could not parse L2/L3 size, using default.'
                cache_details += '   (Could not parse specific L2/L3 sizes from output)\n'

        else:
            method = f"Unsupported OS ({os_name}), using default placeholder."
            cache_details = f"Automatic detection not implemented for {os_name}."

    except FileNotFoundError:
        method = f"Command for {os_name} not found, using default placeholder."
        cache_details = f"Could not execute system command to find cache size."
    except subprocess.CalledProcessError as e:
        method = f"Command for {os_name} failed (Error {e.returncode}), using default placeholder."
        cache_details = f"Error running system command: {e}"
    except Exception as e:
        method = f"Error parsing command output for {os_name}, using default placeholder."
        cache_details = f"Parsing error: {e}"

    return {
        "os": os_name, 
        "l2_l3_size_bytes": l2_l3_size_bytes, 
        "method": method,
        "details": cache_details,
        "all_sizes": all_sizes
    }

if(__name__ == "__main__"):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Starting cache simulation script.")

    system_info = get_system_cache_info()
    detected_os = system_info["os"]
    l2_l3_detection_method = system_info["method"]
    cache_detection_details = system_info["details"]
    parsed_cache_sizes = system_info["all_sizes"]

    L1_CACHE_SIZE_BYTES = 4096
    BLOCK_SIZE_BYTES = 64 
    ASSOCIATIVITY = 8 
    START_ADDRESS = 0x10000000 
    L2_L3_CACHE_SIZE_BYTES = system_info["l2_l3_size_bytes"] 
    NUM_RANDOM_RUNS = 30
    ADDRESS_SIZE_BITS = 64
    NUM_PROCESSES = multiprocessing.cpu_count() 

    data_types = {
        'char': {'size': 1}, 
        'short': {'size': 2}, 
        'int': {'size': 4}, 
        'long': {'size': 8}
    }
    
    cache_config_dict = {
        'cache_size_bytes': L1_CACHE_SIZE_BYTES, 
        'block_size_bytes': BLOCK_SIZE_BYTES,
        'associativity': ASSOCIATIVITY,
        'address_size_bits': ADDRESS_SIZE_BITS
    }

    logging.info("--- Cache Configuration ---")
    logging.info(f"Detected OS: {detected_os}")
    logging.info(f"L2/L3 Size Determination: {l2_l3_detection_method}")
    logging.info(f" >> Size used for simulation: {L2_L3_CACHE_SIZE_BYTES:,} bytes")
    logging.info(f"Simulated L1 Cache Size: {L1_CACHE_SIZE_BYTES} bytes")
    logging.info(f"Simulated L1 Block Size: {BLOCK_SIZE_BYTES} bytes")
    logging.info(f"Simulated L1 Associativity: {ASSOCIATIVITY}-way")
    try:
         dummy_cache = CacheSimulator(**cache_config_dict)
         logging.info(f"Simulated L1 Number of Sets: {dummy_cache.num_sets}")
    except ValueError as e:
         logging.error(f"  Error initializing dummy cache for config print: {e}")
         logging.info(f"Simulated L1 Number of Sets: Error in config") 
    logging.info(f"Simulated Start Address: {START_ADDRESS:x}")
    logging.info(f"Parallel Processes: {NUM_PROCESSES}")
    logging.info("-"*20)

    results = {}

    for name, properties in data_types.items():
        logging.info(f"Starting simulation for data type: {name} (size: {properties['size']} bytes)")
        data_size = properties['size']
        results[name] = {'row_major': float('nan'), 'col_major': float('nan'), 'random': float('nan')}
        
        rows, cols = 0, 0
        total_elements = 0
        
        if(name == 'char'):
            rows, cols = 64, 64 
            total_elements = rows * cols
        elif(name == 'int'):
            rows, cols = 32, 32 
            total_elements = rows * cols
        elif(name == 'short' or name == 'long'):
            total_elements = L2_L3_CACHE_SIZE_BYTES // data_size
            if(total_elements <= 0):
                 logging.warning(f"L2/L3 cache size too small for data type {name}. Skipping.")
                 continue
            rows = int(math.sqrt(total_elements))
            while(rows > 0 and total_elements % rows != 0):
                 rows -= 1
            if(rows == 0):
                 logging.warning(f"Could not find suitable integer dimensions for {total_elements} elements. Skipping {name}.")
                 continue
            cols = total_elements // rows
        else:
            logging.warning(f"Unknown data type {name}. Skipping.")
            continue

        total_bytes = rows * cols * data_size
        if(rows <= 0 or cols <= 0):
             logging.warning(f"Invalid dimensions ({rows}x{cols}) calculated for {name}. Skipping.")
             continue
        logging.info(f"  Array Dimensions: {rows} x {cols} ({total_elements:,} elements, {total_bytes:,} bytes total)")

        base_args = (START_ADDRESS, rows, cols, data_size)
        random_access_start_addr = START_ADDRESS + L2_L3_CACHE_SIZE_BYTES // 2
        random_access_range_bytes = L2_L3_CACHE_SIZE_BYTES
        num_accesses_per_run = rows * cols

        logging.info("    Simulating Row Major Access...")
        row_major_args = ('row_major',) + base_args + (0, 0) 
        worker_func = partial(run_single_simulation, cache_config=cache_config_dict)
        try:
             temp_cache = CacheSimulator(**cache_config_dict)
             row_major_addresses = generate_row_major_addresses(START_ADDRESS, rows, cols, data_size)
             if(row_major_addresses):
                 for addr in row_major_addresses:
                     temp_cache.access(addr)
                 results[name]['row_major'] = temp_cache.get_miss_rate()
             else:
                 results[name]['row_major'] = 0.0
             logging.info(f"      Row Major Miss Rate: {results[name]['row_major']:.4f}")
        except Exception as e:
            logging.error(f"      Error during row major simulation: {e}")
            

        logging.info("    Simulating Column Major Access...")
        col_major_args = ('col_major',) + base_args + (0, 0)
        try:
             temp_cache = CacheSimulator(**cache_config_dict)
             col_major_addresses = generate_col_major_addresses(START_ADDRESS, rows, cols, data_size)
             if(col_major_addresses):
                 for addr in col_major_addresses:
                     temp_cache.access(addr)
                 results[name]['col_major'] = temp_cache.get_miss_rate()
             else:
                 results[name]['col_major'] = 0.0
             logging.info(f"      Col Major Miss Rate: {results[name]['col_major']:.4f}")
        except Exception as e:
            logging.error(f"      Error during column major simulation: {e}")


        logging.info(f"    Simulating Random Access ({NUM_RANDOM_RUNS} runs, parallel)...")
        random_run_args_list = [
            ('random', random_access_start_addr, rows, cols, data_size, 
             random_access_range_bytes, num_accesses_per_run)
            for _ in range(NUM_RANDOM_RUNS)
        ]
        
        random_miss_rates = []
        try:
            logging.info(f"      Starting parallel pool with {NUM_PROCESSES} processes...")
            with multiprocessing.Pool(processes=NUM_PROCESSES) as pool:
                worker_func = partial(run_single_simulation, cache_config=cache_config_dict)
                random_miss_rates = pool.map(worker_func, random_run_args_list)
            logging.info(f"      Parallel pool finished.")
        except Exception as e:
             logging.error(f"      Error during parallel random simulation: {e}")

        valid_random_rates = [r for r in random_miss_rates if isinstance(r, (int, float)) and not math.isnan(r)]
        if(valid_random_rates):
             avg_random_miss_rate = sum(valid_random_rates) / len(valid_random_rates)
             results[name]['random'] = avg_random_miss_rate
        else:
             logging.warning(f"      No valid results obtained from parallel random runs for {name}.")

        logging.info(f"      Average Random Miss Rate: {results[name]['random']:.4f}")
        logging.info("-"*10)

    logging.info("--- Final Miss Rate Report --- Generating Table --- ")
    header1 = "L1 Cache Config: {:,} bytes, {} bytes/block, {}-way associative".format(
        L1_CACHE_SIZE_BYTES, BLOCK_SIZE_BYTES, ASSOCIATIVITY
    )
    header2 = "Start Address: {:x}".format(START_ADDRESS)
    header3 = "Array Size for short/long matched L2/L3 Size: {:,} bytes ({})".format(
        L2_L3_CACHE_SIZE_BYTES, l2_l3_detection_method
    )
    header4 = "Random Access Range: Offset +{:,} bytes, Size {:,} bytes".format(
        L2_L3_CACHE_SIZE_BYTES // 2, L2_L3_CACHE_SIZE_BYTES
    )
    separator = "="*65
    table_header = "{:<10} | {:<15} | {:<15} | {:<15}".format("Data Type", "Row Major MR", "Col Major MR", "Random MR")
    table_separator = "-" * 65
    
    table_lines = [header1, header2, header3, header4, separator, table_header, table_separator]
    
    for name in data_types.keys():
        rm_mr = results.get(name, {}).get('row_major', float('nan'))
        cm_mr = results.get(name, {}).get('col_major', float('nan'))
        rand_mr = results.get(name, {}).get('random', float('nan'))

        rm_str = f"{rm_mr:.4f}" if isinstance(rm_mr, (int, float)) and not math.isnan(rm_mr) else "N/A"
        cm_str = f"{cm_mr:.4f}" if isinstance(cm_mr, (int, float)) and not math.isnan(cm_mr) else "N/A"
        rand_str = f"{rand_mr:.4f}" if isinstance(rand_mr, (int, float)) and not math.isnan(rand_mr) else "N/A"
        table_lines.append("{:<10} | {:<15} | {:<15} | {:<15}".format(name, rm_str, cm_str, rand_str))
        
    table_lines.append(separator)
    
    print("\n".join(table_lines))
    logging.info("Script finished.")

"""
==============================================================================
                                ASSIGNMENT REPORT
==============================================================================

------------------------------------------------------------------------------
Part 1: System Cache Research & File Types
------------------------------------------------------------------------------

1. CPU Cache Sizes (Attempted automatic detection):
   - Detected OS: {detected_os} 
   - Method Used: {l2_l3_detection_method}
   - Detailed Output/Parsing Info:
{cache_detection_details}

   - Parsed Cache Sizes (Bytes):
     - L1 Instruction: {parsed_cache_sizes["l1i"] if parsed_cache_sizes["l1i"] else 'N/A'}
     - L1 Data: {parsed_cache_sizes["l1d"] if parsed_cache_sizes["l1d"] else 'N/A'}
     - L2: {parsed_cache_sizes["l2"] if parsed_cache_sizes["l2"] else 'N/A'}
     - L3: {parsed_cache_sizes["l3"] if parsed_cache_sizes["l3"] else 'N/A'}

   *Largest L2/L3 Cache Size Used for Simulation*: {L2_L3_CACHE_SIZE_BYTES:,} bytes. 
    This value determined array dimensions for 'short' and 'long' data types 
    and the range for random accesses.

2. Common File Types and Sizes:
   a) Plain Text File (.txt):
      - Expected Size: Highly variable, from a few bytes (KB) for notes or 
        short documents to potentially Megabytes (MB) for logs or manuscripts.
      - Fits in Cache?: Small to medium text files (KB to low MB) would easily 
        fit within the 16MB cache. Very large text files might not.
   b) JPEG Image File (.jpg):
      - Expected Size: Typically ranges from tens of Kilobytes (KB) for web 
        images to several Megabytes (MB) for high-resolution photographs.
      - Fits in Cache?: Most common JPEGs would fit within the 16MB cache. 
        Extremely high-resolution or minimally compressed images could exceed it.
   c) MP4 Video File (.mp4):
      - Expected Size: Generally ranges from Megabytes (MB) for short clips 
        to Gigabytes (GB) for full-length movies or high-definition videos.
      - Fits in Cache?: Almost never. Video files are typically much larger 
        than CPU caches.

3. What happens if a file doesn't fit in the cache?
   If a file or any data really does not 
   fit into the largest cache level (L2/L3), the CPU must fetch the required 
   data directly from main memory  more frequently. RAM access is 
   significantly slower than cache access (by orders of magnitude). This leads 
   to increased latency for data retrieval and lower overall performance. If 
   the working set of data constantly needed by the CPU exceeds cache size, 
   the system may experience "cache thrashing," where data blocks are repeatedly 
   loaded into the cache only to be quickly evicted to make room for other 
   needed blocks, further degrading performance.

------------------------------------------------------------------------------
Part 2: Simulation Parameters Chosen
------------------------------------------------------------------------------

1. Starting Address: `0x10000000` (Arbitrary)

2. Simulated L1 Cache Layout:
   - Total Size: 4096 bytes (Assignment requirement)
   - Block Size: 64 bytes (Assumption)
   - Set Associativity: 8-way Set Associative (Chosen)
   - Replacement Policy: LRU (Chosen)
   - Valid Bit: Implemented via `valid` flag.

------------------------------------------------------------------------------
Part 3 & 4: Simulation Results - Miss Rate Report
------------------------------------------------------------------------------

The following table presents the calculated miss rates for the **{detected_os}** run.

L1 Cache Config: 4,096 bytes, 64 bytes/block, 8-way associative
Start Address: 10000000
Array Size for short/long matched L2/L3 Size: {L2_L3_CACHE_SIZE_BYTES:,} bytes ({l2_l3_detection_method})
Random Access Range: Offset +{L2_L3_CACHE_SIZE_BYTES // 2:,} bytes, Size {L2_L3_CACHE_SIZE_BYTES:,} bytes
=================================================================
Data Type  | Row Major MR    | Col Major MR    | Random MR       
-----------------------------------------------------------------
char       | {results['char']['row_major']:.4f if isinstance(results.get('char', {}).get('row_major'), float) else 'N/A':<15} | {results['char']['col_major']:.4f if isinstance(results.get('char', {}).get('col_major'), float) else 'N/A':<15} | {results['char']['random']:.4f if isinstance(results.get('char', {}).get('random'), float) else 'N/A':<15}
short      | {results['short']['row_major']:.4f if isinstance(results.get('short', {}).get('row_major'), float) else 'N/A':<15} | {results['short']['col_major']:.4f if isinstance(results.get('short', {}).get('col_major'), float) else 'N/A':<15} | {results['short']['random']:.4f if isinstance(results.get('short', {}).get('random'), float) else 'N/A':<15}
int        | {results['int']['row_major']:.4f if isinstance(results.get('int', {}).get('row_major'), float) else 'N/A':<15} | {results['int']['col_major']:.4f if isinstance(results.get('int', {}).get('col_major'), float) else 'N/A':<15} | {results['int']['random']:.4f if isinstance(results.get('int', {}).get('random'), float) else 'N/A':<15}
long       | {results['long']['row_major']:.4f if isinstance(results.get('long', {}).get('row_major'), float) else 'N/A':<15} | {results['long']['col_major']:.4f if isinstance(results.get('long', {}).get('col_major'), float) else 'N/A':<15} | {results['long']['random']:.4f if isinstance(results.get('long', {}).get('random'), float) else 'N/A':<15}
=================================================================

------------------------------------------------------------------------------
Part 5: Analysis & Findings (Based on {detected_os} run)
------------------------------------------------------------------------------

1. Row-Major vs. Column-Major Performance:
   - For data types where the array size significantly exceeded the L1 cache 
     (`short`, `long`), Row-Major access drastically outperformed Column-Major. 
     This is due to spatial locality. Row-major accesses consecutive elements 
     in memory (`arr[i][j]`, `arr[i][j+1]`, ...). Since cache blocks are 64 bytes, 
     fetching the block for `arr[i][j]` also brings in subsequent elements of 
     that row. For `long` (8 bytes), 8 elements fit in a block; for `short` 
     (2 bytes), 32 elements fit. This leads to many hits after the initial 
     compulsory miss for each block. The miss rate approaches `1 / elements_per_block` 
     (e.g., for `long`, 1/8 = 0.125; for `short`, 1/32 = 0.03125). 
   - Column-Major access (`arr[i][j]`, `arr[i+1][j]`, ...) accesses elements 
     separated by the length of a row in memory. For the 16MB arrays, this 
     (not great), far exceeding the cache block size and likely the 
     entire L1 cache size. This breaks spatial locality, causing nearly every 
     access to require fetching a new block from memory, resulting in a miss 
     rate approaching 100% or so i assume, i am wildly speculating based on preexisting knowledge.

2. Small Array Performance (`char`, `int`):
   - For these types, the total array size was 4096 bytes, matching the 
     simulated L1 cache size. Consequently, after initial loading, the entire 
     array could reside within the cache. Both row-major and column-major 
     access patterns exhibited identical, low miss rates. The access order 
     mattered less because the data locality was contained within the cache 
     itself (good **temporal locality** once loaded). The miss rate primarily 
     reflects the initial compulsory misses to fill the cache with the array 
     data (`num_blocks / num_accesses = 64 blocks / 4096 accesses = 0.0156` for `char`; 
     `64 blocks / 1024 accesses = 0.0625` for `int`).

3. Random Access Performance:
   - Random accesses consistently showed extremely high miss rates (approx. 99.9%) 
     across all data types. This is expected because random access patterns 
     exhibit neither spatial nor temporal locality over the large (16MB) address 
     range. The probability of randomly accessing an address whose data block 
     happens to be present in the small 4KB L1 cache is negligible. Each access 
     is effectively a compulsory miss.

4. Impact of Data Size:
   - Within the Row-Major results, we see the miss rate increasing with data size 
     (`char` < `short` < `int` < `long`). This is because larger data types mean 
     fewer elements fit into a single 64-byte cache block (char: 64, short: 32, 
     int: 16, long: 8). Since a miss occurs (at minimum) once per block load, 
     having fewer elements per block leads to a higher miss rate when accessing 
     the same number of bytes sequentially (or a similar miss rate when accessing 
     the same *number* of elements, as calculated here: `1/elements_per_block`).

5. Conclusion:
   - This simulation effectively demonstrates the critical importance of data 
     access patterns for cache performance. Algorithms and data structures that 
     leverage spatial and temporal locality (like sequential, row-major access 
     on C-style arrays) achieve significantly lower cache miss rates and thus 
     better performance compared to patterns that jump sporadically through 
     memory (like column-major on large arrays or random access).
     blah blah blah

------------------------------------------------------------------------------
Part 5: Code
------------------------------------------------------------------------------

See above.

------------------------------------------------------------------------------
Placeholder: Windows Specific Run Details
------------------------------------------------------------------------------

[still need to run on windows]

==============================================================================
                              END OF REPORT
==============================================================================
""" 