from fastapi import FastAPI, UploadFile, File
import pandas as pd
from io import BytesIO
from collections import Counter
import re
import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY")
os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"

app = FastAPI()

latest_analysis = {}

class QuestionRequest(BaseModel):
    question: str

llm = init_chat_model(
    model="google/gemini-2.5-flash-lite",
    model_provider="openai"
)

positive_words = [
    "hızlı", "güzel", "temiz", "teşekkür", "lezzetli",
    "iyi", "sıcak", "memnun", "başarılı", "harika",
    "mükemmel", "tavsiye", "özenli"
]

negative_words = [
    "unutulmuş", "geç", "beklettiler", "kötü", "soğuk",
    "eksik", "yanlış", "berbat", "beğenmedim", "şikayet",
    "pişman", "bir daha", "memnun değilim"
]

stop_words = [
    "bir", "ve", "de", "da", "çok", "ama", "için", "ile",
    "bu", "şu", "o", "ben", "daha", "her", "gibi",
    "sipariş", "geldi", "yemek"
]

category_keywords = {
    "Teslimat": ["geç", "bekledim", "beklettiler", "teslimat", "kurye", "saat", "gecikti"],
    "Eksik/Yanlış Ürün": ["eksik", "unutulmuş", "yanlış", "gelmedi", "unutuldu"],
    "Lezzet/Kalite": ["soğuk", "kötü", "berbat", "lezzetsiz", "pişmemiş", "bayat"],
    "Paketleme": ["paket", "dökülmüş", "ezilmiş", "akmış", "dağılmış"],
    "Memnuniyet": ["teşekkür", "hızlı", "güzel", "memnun", "harika", "mükemmel"]
}

def detect_category(review):
    review = review.lower()

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in review:
                return category

    return "Diğer"

def get_top_words(reviews, limit=10):
    all_text = " ".join(reviews).lower()
    words = re.findall(r"\b\w+\b", all_text)

    filtered_words = [
        word for word in words
        if word not in stop_words and len(word) > 2
    ]

    word_counts = Counter(filtered_words)
    return word_counts.most_common(limit)


def analyze_sentiment(review):
    review = review.lower()

    positive_score = sum(1 for word in positive_words if word in review)
    negative_score = sum(1 for word in negative_words if word in review)

    if positive_score > negative_score:
        return "Pozitif"
    elif negative_score > positive_score:
        return "Negatif"
    else:
        return "Nötr"

@app.get("/")
def home():
    return {"message": "AI Customer Review Analytics API Running"}

@app.post("/upload_reviews")
async def upload_reviews(file: UploadFile = File(...)):
    contents = await file.read()
    df = pd.read_excel(BytesIO(contents))

    if "Yorum" not in df.columns:
        return {"error": "Excel dosyasında 'Yorum' sütunu bulunamadı."}

    df = df.dropna(subset=["Yorum"])
    df["Yorum"] = df["Yorum"].astype(str)
    df["Sentiment"] = df["Yorum"].apply(analyze_sentiment)
    df["Category"] = df["Yorum"].apply(detect_category)

    sentiment_counts = df["Sentiment"].value_counts().to_dict()
    category_counts = df["Category"].value_counts().to_dict()
    positive_count = sentiment_counts.get("Pozitif", 0)
    neutral_count = sentiment_counts.get("Nötr", 0)
    negative_count = sentiment_counts.get("Negatif", 0)

    positive_pct = round((positive_count / len(df)) * 100, 1)
    neutral_pct = round((neutral_count / len(df)) * 100, 1)
    negative_pct = round((negative_count / len(df)) * 100, 1)

    negative_reviews = (
        df[df["Sentiment"] == "Negatif"]["Yorum"]
        .head(10)
        .tolist()
    )

    top_words = get_top_words(df["Yorum"].tolist())

    summary_prompt = f"""
    You are a customer review analytics assistant.

    Analyze the following review analytics results and write a short business summary in Turkish.

    Total reviews: {len(df)}

    Sentiment counts:
    Positive: {positive_count}
    Neutral: {neutral_count}
    Negative: {negative_count}

    Sentiment percentages:
    Positive: %{positive_pct}
    Neutral: %{neutral_pct}
    Negative: %{negative_pct}

    Most frequent words:
    {top_words}

    Top negative reviews:
    {negative_reviews}

    Write the answer in Turkish with exactly these sections:

    Genel Durum
    Müşteri memnuniyetinin genel seviyesini açıkla.

    Güçlü Yönler
    Müşterilerin en çok memnun kaldığı noktaları yaz.

    Şikayet Konuları
    Negatif yorumlarda öne çıkan problemleri yaz.

    İşletme Önerileri
    İşletme için 3 uygulanabilir öneri yaz.
    """

    ai_summary = llm.invoke(summary_prompt).content
    action_plan_prompt = f"""
    You are a customer experience strategy assistant.

    Create an action plan in Turkish based on the review analysis results.

    Total reviews: {len(df)}

    Sentiment counts:
    Positive: {positive_count}
    Neutral: {neutral_count}
    Negative: {negative_count}

    Category counts:
    {category_counts}

    Top negative reviews:
    {negative_reviews}

    Write the answer with exactly these sections:

    1. En Kritik Problem
    En önemli müşteri problemini açıkla.

    2. Önceliklendirilmiş Aksiyonlar
    3 maddelik uygulanabilir aksiyon planı yaz.

    3. Beklenen Etki
    Bu aksiyonlar uygulanırsa müşteri deneyiminde nasıl bir iyileşme beklenir?
    """

    ai_action_plan = llm.invoke(action_plan_prompt).content

    global latest_analysis

    latest_analysis = {
        "total_reviews": len(df),
        "sentiment_counts": sentiment_counts,
        "sentiment_percentages": {
            "Pozitif": positive_pct,
            "Nötr": neutral_pct,
            "Negatif": negative_pct
        },
        "top_words": top_words,
        "negative_reviews": negative_reviews,
        "sample_reviews": df[["Yorum", "Sentiment"]].head(20).to_dict(orient="records"),
        "ai_summary": ai_summary,
        "category_counts": category_counts,
        "ai_action_plan": ai_action_plan
    }

    return {
        "total_reviews": len(df),
        "columns": list(df.columns),
        "sample_reviews": df[["Yorum", "Sentiment"]].head(5).to_dict(orient="records"),
        "sentiment_counts": sentiment_counts,
        "negative_reviews": negative_reviews,
        "top_words": top_words,
        "sentiment_percentages": {
            "Pozitif": positive_pct,
            "Nötr": neutral_pct,
            "Negatif": negative_pct
        },
        "ai_summary": ai_summary,
        "category_counts": category_counts,
        "ai_action_plan": ai_action_plan
    }

@app.post("/ask_reviews")
def ask_reviews(request: QuestionRequest):
    if not latest_analysis:
        return {
            "answer": "Önce Excel dosyasını yükleyip analiz etmelisiniz."
        }

    prompt = f"""
    You are an AI customer review analytics assistant.

    Answer the user's question in Turkish based only on the following analysis results.

    Analysis results:
    {latest_analysis}

    User question:
    {request.question}

    Give a clear, short and business-focused answer.
    """

    answer = llm.invoke(prompt).content

    return {
        "answer": answer
    }

    
   




