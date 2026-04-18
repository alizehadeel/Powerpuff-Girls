import json
from spam_classification import extract_features, classify_email
from extractor import process_eml
from rank import beautify_output, rank_opportunities

extracted_list=[]
student = {
        "name":             "Amina",
        "gpa":              3.4,
        "degree":           "CS",
        "semester":         6,
        "skills":           ["python", "ml", "c++"],
        "interests":        ["AI", "research"],
        "preferred_type":   ["internship", "competition"],
        "preferences": {
            "mode":         "remote",
            "paid":         True,
            "max_hours":    20
        },
        "past_experiences": ["internship", "research"]
    }

def process(filename):
    """Main function to classify email (1).eml and store result in dictionary."""
    # Classify the email and store the result in a dictionary
    result_dict = classify_email(filename)
    
    # Print the classification result for verification
    print("Classification Result:")
    print(result_dict)
    
    # If classification was successful, check if it's spam
    if result_dict["status"] == "success":
        # Parse the JSON result to check is_spam
        classification_data = json.loads(result_dict["result"])
        is_spam = classification_data.get("is_spam", True)
        
        # If it's not spam, process it with the extractor
        if not is_spam:
            print("\nEmail is not spam. Extracting structured data...")
            extracted_data = process_eml(filename)
            extracted_list.append(extracted_data)
            # print("\nExtracted Structured Data:")
            # print(json.dumps(extracted_data, indent=2))

        else:
            print("\nEmail is classified as spam. Skipping extraction.")
    


def main():
    for filename in ["email (1).eml", "email (2).eml", "email (3).eml", "email (4).eml", "email (5).eml"]:
        process(filename)
    # print(extracted_list)
    results=rank_opportunities(extracted_list, student)
    print("\nRanked Opportunities:", results)

    raw_output = f"\n========== RANKED FOR {student['name'].upper()} ==========\n\n"
    for i, r in enumerate(results, 1):
        paid_label  = "Paid" if r["paid"] else "Unpaid"
        hours_label = f"{r['hours_per_week']} hrs/week" if r["hours_per_week"] else "hours unspecified"
        raw_output += f"#{i}  {r['title']}\n"
        raw_output += f"     Type:     {r['type']} | {paid_label} | {r['mode']} | {hours_label}\n"
        raw_output += f"     Deadline: {r['deadline']}\n"
        raw_output += f"     Score:    {r['score']}\n"
        raw_output += f"     Reason:   {r['reason']}\n\n"

    # Print raw then beautified
    print(raw_output)
    print("\n========== BEAUTIFIED OUTPUT ==========\n")
    print(beautify_output(raw_output))



if __name__ == "__main__":
    main()