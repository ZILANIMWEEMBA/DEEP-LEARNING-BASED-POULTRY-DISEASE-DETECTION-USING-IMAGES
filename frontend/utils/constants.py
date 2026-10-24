import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
CLASS_NAMES = ["Healthy", "Coccidiosis", "Newcastle Disease", "Salmonella"]
AI_TITLE = "AI Care Suggestion – Not a Prescription"
AI_DISCLAIMER = ("AI prediction is for decision-support purposes only. Final diagnosis and treatment "
                 "must be confirmed by a qualified veterinarian.")
CONFIDENCE_NOTE = ("This confidence reflects the model's classification output and does not confirm "
                   "a veterinary diagnosis.")
LIMITATIONS = [
    "Image-based classification is not equivalent to laboratory diagnosis.",
    "Similar diseases can look alike; image quality affects the result.",
    "Farm conditions may differ from the data the model learned from.",
    "Model confidence is not clinical certainty. The veterinarian has the final word.",
]
