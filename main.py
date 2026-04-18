from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
app = FastAPI()


student_db = {}
email_db = {}
class EmailData(BaseModel):
    subject: str
    body: str
class StudentProfile(BaseModel):
    name: str
    gpa: float
    degree: str
    semester: int

    skills: List[str]
    interests: List[str]
    preferences: List[str]

    financial_need: str
    location: str

    past_experiences: List[str]
    
class AnalyzeRequest(BaseModel):
    profile: StudentProfile
    emails: List[EmailData]
@app.get("/")
def home():
    return {"message": "Backend is running"}


# getting form data
@app.post("/student/profile")
def store_profile(profile: StudentProfile):

    student_db[profile.name] = profile.model_dump()

    return {
        "message": "Profile stored",
        "profile": profile.model_dump()
    }
    

    
# @app.post("/analyze")
# def analyze(data: AnalyzeRequest):

    profile = data.profile
    emails = data.emails

    results = []

    for email in emails:

        text = (email.subject + " " + email.body).lower()

        score = 0

        # simple intelligent scoring (better than fixed 85)
        for skill in profile.skills:
            if skill.lower() in text:
                score += 25

        for interest in profile.interests:
            if interest.lower() in text:
                score += 15

        if "internship" in text:
            score += 30

        if "scholarship" in text:
            score += 30

        if "deadline" in text or "apply" in text:
            score += 20

        results.append({
            "subject": email.subject,
            "score": min(score, 100),
            "reason": "AI-lite match based on skills, interests & opportunity keywords"
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return {
        "profile": profile.model_dump(),
        "ranked_opportunities": results
    }

    profile = data.profile
    emails = data.emails

    # 🔥 fake AI logic (replace later)
    results = []

    for email in emails:
        results.append({
            "subject": email.subject,
            "score": 85,
            "reason": "Matches skills + opportunity detected"
        })

    return {
        "profile": profile.model_dump(),
        "ranked_opportunities": results
    }


@app.post("/analyze")
async def analyze(
    profile: str = Form(...),
    files: List[UploadFile] = File(...)
):
    # Parse profile
    profile_data = json.loads(profile)
    profile_obj = StudentProfile(**profile_data)
    
    results = []
    
    for file in files:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eml') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # JUST SEND THE FILE PATH to your server.py - NO AI logic here
        ai_result = process(temp_path)  # Your server.py does everything
        
        # Clean up
        os.unlink(temp_path)
        
        # Use the result from your server.py
        results.append({
            "subject": file.filename,
            "score": 85,  # Your server.py would return this
            "reason": "Processed by server.py"
        })
    
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    
    return {
        "profile": profile_obj.model_dump(),
        "ranked_opportunities": results
    }
@app.post("/emails")
def store_emails(emails: List[EmailData]):

    email_db["batch"] = [e.model_dump() for e in emails]

    return {
        "message": "Emails stored",
        "emails": email_db["batch"]
    }