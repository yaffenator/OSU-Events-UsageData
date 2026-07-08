import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import sys

# Initialize Firebase Admin
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    sys.exit(1)

"""Helper to ensure the user enters a valid YYYY-MM-DD date."""
def get_valid_date(prompt_text):
    while True:
        date_str = input(prompt_text).strip()
        try:
            # Test if it matches the required format
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            print("Invalid format. Please use YYYY-MM-DD (e.g., 2025-09-16).")

def run_extraction():
    print("\n--- Honors College Data Extraction ---")
    
    # Get dynamic inputs from the user
    term_name = input("Enter a label for this extraction (e.g., Fall 2025, Custom Range): ").strip()
    start_date = get_valid_date("Enter the Start Date (YYYY-MM-DD): ")
    end_date = get_valid_date("Enter the End Date (YYYY-MM-DD): ")

    # Sanity check
    if start_date > end_date:
        print("Error: Start Date cannot be after the End Date. Exiting.")
        return

    print(f"\nQuerying Firestore for '{term_name}' ({start_date} to {end_date})...")
    print("This may take a moment depending on the date range.\n")
    
    # Query Firestore using the dynamic dates
    usage_ref = db.collection('StudentUsage')
    query = usage_ref.where('date', '>=', start_date).where('date', '<=', end_date)
    docs = query.stream()

    extracted_data = {}

    for doc in docs:
        doc_data = doc.to_dict()
        opened_users = doc_data.get('openedUsers', {})
        
        for user_id, user_info in opened_users.items():
            departments = user_info.get('departments', [])
            
            # Check if they are affiliated with the Honors College
            is_hc = any("Honors College" in str(dept) for dept in departments)
            
            if is_hc:
                classification = user_info.get('classification', 'Other')
                
                # Using a tuple key ensures a student is only counted once per term/range
                record_key = (term_name, user_id)
                if record_key not in extracted_data:
                    extracted_data[record_key] = classification

    # Format data for export
    if not extracted_data:
        print(f"No Honors College users found between {start_date} and {end_date}.")
        return
        
    print(f"Extraction complete. Found {len(extracted_data)} unique records.")
    
    export_list = []
    for (term, user_id), classification in extracted_data.items():
        export_list.append({
            "Label": term,
            "User ID": user_id,
            "Classification": classification
        })

    # Export to CSV using Pandas
    df = pd.DataFrame(export_list)
    
    # Sort by Classification for a cleaner spreadsheet
    df = df.sort_values(by=["Classification"])
    
    # Clean up the term name to make a safe filename (removes weird characters)
    safe_term_name = "".join(c for c in term_name if c.isalnum() or c in (' ', '_')).replace(' ', '_')
    filename = f"HonorsCollege_Usage_{safe_term_name}.csv"
    
    df.to_csv(filename, index=False)
    
    print(f"Data successfully written to {filename}")

if __name__ == "__main__":
    run_extraction()
