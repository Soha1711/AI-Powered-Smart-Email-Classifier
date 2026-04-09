from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import os
import database
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

app = FastAPI(title="Email Intelligence API")

# Path configs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(os.path.dirname(BASE_DIR), "models")
CAT_MODEL_PATH = os.path.join(MODELS_DIR, "distilbert_category")
URG_MODEL_PATH = os.path.join(MODELS_DIR, "distilbert_urgency")

# Global variables for models
cat_tokenizer = None
cat_model = None
urg_tokenizer = None
urg_model = None

# Legacy Fallback Models
legacy_cat = None
legacy_urg = None

# Initialize DB on startup
@app.on_event("startup")
def on_startup():
    database.init_db()

def load_brain():
    global cat_tokenizer, cat_model, urg_tokenizer, urg_model, legacy_cat, legacy_urg
    
    # 1. Load Legacy Models (Joblib) as fallback
    try:
        legacy_cat = joblib.load(os.path.join(BASE_DIR, "category_pipeline.pkl"))
        legacy_urg = joblib.load(os.path.join(BASE_DIR, "urgency_pipeline.pkl"))
        print("Legacy Brains Loaded!")
    except Exception as e:
        print(f"Legacy loading error: {e}")

    # 2. Load DistilBERT (if ready)
    try:
        if os.path.exists(CAT_MODEL_PATH) and os.path.exists(os.path.join(CAT_MODEL_PATH, "config.json")):
            cat_tokenizer = AutoTokenizer.from_pretrained(CAT_MODEL_PATH)
            cat_model = AutoModelForSequenceClassification.from_pretrained(CAT_MODEL_PATH)
            print("Category Brain Loaded!")
        
        if os.path.exists(URG_MODEL_PATH) and os.path.exists(os.path.join(URG_MODEL_PATH, "config.json")):
            urg_tokenizer = AutoTokenizer.from_pretrained(URG_MODEL_PATH)
            urg_model = AutoModelForSequenceClassification.from_pretrained(URG_MODEL_PATH)
            print("Urgency Brain Loaded!")
    except Exception as e:
        print(f"Brain loading error: {e}")

# Try loading once at startup
load_brain()

class EmailRequest(BaseModel):
    sender: str
    subject: str
    text: str

# --- HYBRID ENGINE HELPERS ---
def hybrid_overrides(text, subject):
    full_text = f"{subject} {text}".lower()
    overrides = {}
    
    # 1. Category Detection (Priority order: Spam > Complaint > Request > Feedback)
    
    # Spam
    spam_kws = ["win", "winner", "won", "congratulations", "congrats", "prize", "reward", "gift", "free", "free offer", "limited time", "exclusive offer", "special offer", "claim now", "click here", "click below", "act now", "hurry up", "urgent offer", "instant reward", "guaranteed", "no risk", "risk free", "earn money", "make money", "work from home", "easy income", "passive income", "get rich", "millionaire", "investment opportunity", "crypto offer", "bitcoin offer", "double your money", "loan offer", "instant loan", "credit card offer", "pre-approved", "no credit check", "discount", "huge discount", "sale", "clearance sale", "90% off", "buy now", "subscribe now", "join now", "register now", "sign up now", "limited stock", "offer expires", "final notice", "urgent action required", "verify account", "update account", "phishing alert", "suspicious link", "unknown link", "click link", "download now", "install now", "virus alert", "security alert fake", "lottery", "jackpot", "lucky draw", "selected winner", "claim prize", "bank alert fake", "otp scam", "fake payment", "scam", "fraud", "phishing", "suspicious email", "spam message", "advertisement", "promo", "promotion", "marketing email", "bulk email", "newsletter unwanted", "unsubscribe here", "hidden link", "random link", "shortened url", "bit.ly link", "unknown sender", "suspicious attachment", "free trial", "bonus offer", "cashback offer", "referral bonus"]
    if any(kw in full_text for kw in spam_kws):
        overrides["category"] = "spam"
        
    # Complaint
    complaint_kws = ["issue", "problem", "error", "bug", "failure", "failed", "not working", "broken", "crash", "crashing", "stuck", "unable", "cannot", "can't", "won't", "delay", "delayed", "slow", "lag", "glitch", "defect", "complaint", "dissatisfied", "unhappy", "frustrated", "disappointed", "unacceptable", "worst", "terrible", "bad experience", "poor service", "incorrect", "wrong", "missing", "not received", "damaged", "defective", "outage", "downtime", "not responding", "timeout", "access denied", "login issue", "payment failed", "transaction failed", "refund not received", "charged twice", "overcharged", "unauthorized", "security issue", "hacked", "breach", "data loss", "system down", "server down", "urgent issue", "critical issue", "escalation", "escalate", "fix immediately", "needs fixing", "unresolved", "still facing", "repeat issue", "persistent issue", "failure to load", "error message", "bug report", "unable to access", "not opening", "freezing", "crash report", "not updated", "malfunction", "unexpected behavior", "broken link", "missing data", "incorrect data", "wrong information", "duplicate charge", "service unavailable", "no response", "waiting too long", "no update", "ignored", "not fixed", "support not responding", "complaint regarding", "facing problem", "experiencing issue", "trouble accessing", "unable to proceed", "cannot complete", "system error", "application error", "login failed"]
    if any(kw in full_text for kw in complaint_kws):
        overrides["category"] = "complaint"
        
    # Request
    request_kws = ["request", "please provide", "kindly provide", "please send", "kindly send", "need", "require", "required", "requesting", "would like", "i want", "can you", "could you", "please help", "assist", "assistance", "support needed", "help me", "guide me", "clarify", "explanation needed", "provide details", "share information", "send details", "need information", "inquiry", "enquiry", "asking for", "request for", "need access", "grant access", "reset password", "update details", "change details", "modify", "update", "edit", "upgrade", "downgrade", "subscription request", "activate", "deactivate", "enable", "disable", "register", "sign up", "create account", "delete account", "cancel account", "cancel subscription", "schedule", "book", "reschedule", "appointment request", "document request", "invoice request", "statement request", "report request", "download request", "provide link", "send link", "verification request", "confirm", "confirmation needed", "follow up request", "check status", "status update", "track order", "tracking request", "request callback", "call me", "contact me", "connect me", "escalate request", "priority request", "quick help needed", "urgent request", "immediate assistance", "request update", "share file", "send attachment", "provide solution", "request explanation", "need clarification", "request approval", "request extension", "deadline extension", "access request", "login help", "account unlock", "unlock account"]
    if any(kw in full_text for kw in request_kws):
        if "category" not in overrides:
            overrides["category"] = "request"
        
    # Feedback
    feedback_kws = ["feedback", "suggestion", "recommend", "recommendation", "opinion", "review", "rating", "experience", "user experience", "ux", "ui", "interface", "design", "usability", "improvement", "improve", "enhancement", "enhance", "better", "could be better", "needs improvement", "like", "liked", "love", "loved", "dislike", "disliked", "hate", "hated", "satisfied", "unsatisfied", "happy", "unhappy", "impressed", "not impressed", "good", "great", "excellent", "amazing", "awesome", "fantastic", "perfect", "nice", "decent", "average", "okay", "fine", "poor", "bad", "worst experience", "best experience", "smooth", "easy to use", "difficult to use", "confusing", "complicated", "simple", "intuitive", "slow but okay", "fast and smooth", "performance feedback", "quality feedback", "service feedback", "product feedback", "feature request", "new feature suggestion", "add feature", "remove feature", "change feature", "feedback regarding", "comments", "thoughts", "opinion on", "review of service", "rating given", "star rating", "overall experience", "customer feedback", "user feedback", "constructive feedback", "criticism", "positive feedback", "negative feedback", "neutral feedback", "appreciation", "praise", "complaint-like feedback", "minor issue", "small issue", "usability issue", "design issue", "navigation issue"]
    if any(kw in full_text for kw in feedback_kws):
        if "category" not in overrides:
            overrides["category"] = "feedback"
            
    # 2. Urgency Detection (Checked in order: Low -> Medium -> High to handle negations)
    
    # Check for Low Urgency first (Implicitly handles "Not urgent")
    low_urg_kws = ["not urgent", "no urgency", "whenever possible", "no rush", "take your time", "at your convenience", "when convenient", "no hurry", "low priority", "minor issue", "small issue", "trivial issue", "slight issue", "suggestion", "feedback", "general feedback", "just sharing", "for your information", "fyi", "optional", "optional request", "if possible", "whenever you get time", "no immediate action", "can wait", "not time sensitive", "not critical", "not important urgently", "informational", "just checking", "casual inquiry", "general inquiry", "general question", "query", "simple question", "curiosity", "wondering", "wanted to know", "would like to know", "just asking", "not pressing", "no pressure", "relaxed timeline", "flexible timeline", "long term", "future request", "future consideration", "improvement suggestion", "feature suggestion", "enhancement idea", "nice to have", "good to have", "optional improvement", "not necessary", "not required immediately", "can be delayed", "delay acceptable", "no deadline", "flexible deadline", "not impacting work", "no impact", "minimal impact", "low impact", "minor inconvenience", "small inconvenience", "general suggestion", "appreciation message", "praise", "positive feedback", "no action needed", "fyi only", "informational message"]
    if any(kw in full_text for kw in low_urg_kws):
        overrides["urgency"] = "low"
    
    # Check for Medium Urgency
    medium_urg_kws = ["soon", "as soon as possible", "asap (soft)", "early", "priority", "moderate priority", "important", "needs attention", "please check", "please look into", "kindly check", "kindly look into", "follow up", "following up", "waiting for response", "waiting", "delayed", "slight delay", "taking time", "not resolved yet", "still facing", "ongoing issue", "recurring issue", "intermittent issue", "sometimes not working", "occasional problem", "not consistent", "moderate issue", "moderate problem", "needs fixing", "requires attention", "requires review", "check when possible", "resolve soon", "respond soon", "please respond", "would appreciate quick response", "not urgent but important", "whenever possible soon", "request soon", "help soon", "assistance needed soon", "not immediate but needed", "time sensitive moderate", "deadline approaching", "before deadline soon", "medium priority request", "priority medium", "regular issue", "noticeable issue", "inconvenience caused", "slightly frustrating", "needs improvement soon", "needs update soon", "pending issue", "pending request", "update needed", "status needed", "status update", "follow up request", "reminder", "gentle reminder", "second request", "please update", "checking status", "need response", "awaiting reply", "not critical but important", "requires action soon", "moderate impact", "manageable issue", "not severe", "not critical", "not urgent but required"]
    if "urgency" not in overrides and any(kw in full_text for kw in medium_urg_kws):
        overrides["urgency"] = "medium"
        
    # Check for High Urgency (Only if not already set to Low/Medium)
    high_urg_kws = ["urgent", "urgently", "asap", "immediately", "right now", "at once", "critical", "critical issue", "emergency", "high priority", "top priority", "severe", "severe issue", "major issue", "blocking", "blocker", "system down", "server down", "service down", "outage", "downtime", "not working at all", "completely broken", "cannot access", "unable to access", "access denied", "login failed repeatedly", "payment failed urgently", "transaction failed", "data loss", "security breach", "hacked", "fraud", "unauthorized access", "account compromised", "fix immediately", "resolve immediately", "needs immediate attention", "immediate action required", "action required now", "escalate immediately", "escalation required", "urgent fix needed", "immediate support needed", "quick resolution required", "respond immediately", "reply urgently", "please respond asap", "time sensitive", "deadline today", "deadline missed", "before deadline", "urgent request", "urgent help", "urgent assistance", "immediate help", "immediate assistance", "emergency request", "production issue", "production down", "business impacted", "financial loss", "loss occurring", "critical failure", "high impact issue", "cannot proceed", "blocking work", "work stopped", "service unavailable", "major outage", "crash", "crashing repeatedly", "failure to load completely", "system failure", "serious issue", "urgent complaint", "immediate complaint", "immediate escalation", "must fix now", "do it now", "no delay", "without delay", "time critical", "extremely urgent", "very urgent"]
    if "urgency" not in overrides and any(kw in full_text for kw in high_urg_kws):
        overrides["urgency"] = "high"
    # Apply category-based defaults if still unknown
    if "urgency" not in overrides:
        cat = overrides.get("category", "")
        if cat == "complaint":
            overrides["urgency"] = "high"
        elif cat == "request":
            overrides["urgency"] = "medium"
        elif cat == "spam":
            overrides["urgency"] = "low"
        elif cat == "feedback":
            overrides["urgency"] = "low"
            
    return overrides

@app.get("/")
def root():
    return {"status": "Backend running", "brains_loaded": cat_model is not None}

@app.get("/emails")
def get_emails():
    return {"emails": database.get_all_emails()}

@app.delete("/emails")
def delete_emails():
    database.clear_all_emails()
    return {"status": "Database cleared"}

# ===== LEGACY LABEL MAP =====
LEGACY_CAT_MAP = {0: "complaint", 1: "request", 2: "feedback", 3: "spam"}
LEGACY_URG_MAP = {0: "low", 1: "medium", 2: "high"}

@app.post("/predict")
def predict_email(data: EmailRequest):
    text = data.text
    subject = data.subject
    
    # 1. Base Predictions
    pred_cat = "request"
    pred_urg = "medium"
    
    # Level 1: DistilBERT
    if cat_model and cat_tokenizer:
        inputs = cat_tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            outputs = cat_model(**inputs)
        label_id = torch.argmax(outputs.logits).item()
        pred_cat = cat_model.config.id2label[label_id]
        
    if urg_model and urg_tokenizer:
        inputs = urg_tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            outputs = urg_model(**inputs)
        label_id = torch.argmax(outputs.logits).item()
        pred_urg = urg_model.config.id2label[label_id]
        
    # Level 2: Legacy Fallback
    elif legacy_cat and legacy_urg:
        l_cat_res = legacy_cat.predict([text])[0]
        l_urg_res = legacy_urg.predict([text])[0]
        pred_cat = LEGACY_CAT_MAP.get(l_cat_res, "request")
        pred_urg = LEGACY_URG_MAP.get(l_urg_res, "medium")
    
    # 2. Apply High-Priority Hybrid Overrides (Final Layer)
    overrides = hybrid_overrides(text, subject)
    final_cat = overrides.get("category", pred_cat)
    final_urg = overrides.get("urgency", pred_urg)
    
    # Final Safety Check
    if final_urg not in ["low", "medium", "high"]:
        final_urg = "medium"

    # Save to db
    saved_email = database.save_email(
        sender=data.sender,
        subject=data.subject,
        body=text,
        category=final_cat,
        urgency=final_urg
    )

    return saved_email
