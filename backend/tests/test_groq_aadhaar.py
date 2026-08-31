import asyncio
from backend.pipeline.llm_adapters import llm_adapter

async def main():
    text = (
        "भारत सरकार / Government of India\n"
        "Unique Identification Authority of India\n"
        "नाव / Name: राजेश संजय पन्हाळकर / Rajesh Sanjay Panhalkar\n"
        "जन्म दिनांक / DOB: 1999-10-15\n"
        "लिंग / Gender: Male / पुरुष\n"
        "आधार क्रमांक / Your Aadhaar No.: 7708 2761 0853\n"
        "पत्ता: 402, शांति निकेतन, दादर, मुंबई 400014"
    )
    res = await llm_adapter.call_groq(text)
    import json
    print("Groq Result Extracted Successfully:")
    print(json.dumps(res, indent=2, ensure_ascii=True))

if __name__ == "__main__":
    asyncio.run(main())
