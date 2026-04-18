

import os
import email
from email import policy
from concurrent.futures import ThreadPoolExecutor
from google import genai


# Initialize the Gemini Client
# Ensure your environment variable GEMINI_API_KEY is set
client = genai.Client(api_key='AIzaSyBeZQ1QJtyGPq2uQGvlDiafGIQ9mt-ur6I')

def extract_features(file_path):
    """Parses .eml file and extracts relevant features."""
    with open(file_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    # Extract structural and content features
    features = {
        "from": msg.get("From"),
        "subject": msg.get("Subject"),
        "has_attachments": bool(msg.iter_attachments()),
        "attachment_names": [att.get_filename() for att in msg.iter_attachments() if att.get_filename()],
        "body": msg.get_body(preferencelist=('plain')).get_content()[:2000] # Limit size for token efficiency
    }
    return features

def classify_email(eml_path):
    """Parses email and calls Gemini to classify it."""
    try:
        data = extract_features(eml_path)
        
        prompt = f"""
        Analyze the following email and classify as 'Spam' or 'Ham'.
        From: {data['from']}
        Subject: {data['subject']}
        Attachments: {data['attachment_names']}
        Body Preview: {data['body']}
        
        Output only a JSON object: {{"is_spam": boolean, "reason": "short explanation"}}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        print(response.text)  # Debugging output
        return {"file": eml_path, "result": response.text, "status": "success"}
    
    except Exception as e:
        return {"file": eml_path, "error": str(e), "status": "failed"}

for eml in ["email (1).eml", "email (2).eml", "email (3).eml", "email (4).eml", "email (5).eml"]:
    result = classify_email(eml)
    print(result)   


# def process_batch(file_paths, max_workers=5):
#     """Processes a batch of files using a thread pool."""
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         results = list(executor.map(classify_email, file_paths))
#     return results


# files = ["email (1).eml", "email (2).eml", "email (3).eml", "email (4).eml", "email (5).eml"]
# batch_results = process_batch(files)

# for result in batch_results:
#     if result["status"] == "success":
#         print(f"File: {result['file']}, Classification Result: {result['result']}")
#     else:
#         print(f"File: {result['file']}, Error: {result['error']}")

# #grok llama force scout
# #google-genai


#   import google.generativeai as genai
# Classification Result:
# {'file': 'email (1).eml', 'error': "'Models' object has no attribute 'generate_content'", 'status': 'failed'}

# ```
