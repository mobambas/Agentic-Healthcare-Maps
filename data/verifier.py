import json
import os

def verify_labels(input_filepath, output_filepath):
    """
    Reads a JSONL file, presents records for human verification, 
    and writes the verified records to a new JSONL file.
    """
    verified_records = []

    # Open the original JSONL file for reading
    with open(input_filepath, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    print(f"Loaded {len(lines)} records for verification.\n")

    for index, line in enumerate(lines):
        record = json.loads(line)
        labels = record.get("proposed_labels", {})
        
        # Display the record details
        print("-" * 50)
        print(f"Record {index + 1} of {len(lines)}")
        print(f"Facility Name: {labels.get('facility_name')}")
        print(f"Category: {labels.get('facility_category')}")
        print("Capabilities:")
        
        for cap in labels.get("capabilities", []):
            print(f"  - {cap.get('name')}: '{cap.get('evidence_quote')}'")
        
        print("-" * 50)

        # Prompt the user for verification
        action = input("Does this look correct? Press 'y' to verify, 's' to skip, or 'q' to quit: ").strip().lower()

        if action == 'q':
            print("Exiting verification process...")
            break
        elif action == 'y':
            # Update the human_verified flag to true
            record['human_verified'] = True
            print("Record verified and updated!")
        else:
            print("Record skipped (remains unverified).")

        verified_records.append(record)

    # Save the updated records to the new file
    with open(output_filepath, 'w', encoding='utf-8') as outfile:
        for rec in verified_records:
            json.dump(rec, outfile)
            outfile.write('\n')
            
    print(f"\nSaved {len(verified_records)} records to {output_filepath}")

if __name__ == "__main__":
    # Define your file paths here
    INPUT_FILE = "/Users/test/Documents/Agentic-Healthcare-Maps/data/gold_labels.jsonl"
    OUTPUT_FILE = "/Users/test/Documents/Agentic-Healthcare-Maps/data/verified_gold_labels.jsonl"
    
    # Run the function if the input file exists
    if os.path.exists(INPUT_FILE):
        verify_labels(INPUT_FILE, OUTPUT_FILE)
    else:
        print(f"Error: Could not find the file at {INPUT_FILE}")