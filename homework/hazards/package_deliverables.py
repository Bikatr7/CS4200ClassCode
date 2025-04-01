import tarfile
import os

## I switch between mac and windows so this is basically needed

def main():
    files = [
        'unrolled_instructions.bin',
        'unrolled_simulation.csv',
        'branch_instructions.bin',
        'branch_simulation.csv',
        'hazards_instructions.bin',
        'hazards_simulation.csv',
        'dynamic_reorder.txt',
        'dynamic_instructions.bin',
        'dynamic_simulation.csv',
    ]
    
    with tarfile.open('deliverables.tar', 'w') as tar:
        for file in files:
            if(os.path.exists(file)):
                tar.add(file)
            else:
                print(f"Warning: {file} not found lol")

if(__name__ == "__main__"):
    main() 