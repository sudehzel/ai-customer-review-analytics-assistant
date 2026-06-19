import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from io import BytesIO
from wordcloud import WordCloud
import matplotlib.pyplot as plt


def create_wordcloud(top_words):
    word_freq = {word: count for word, count in top_words}

    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color="white"
    ).generate_from_frequencies(word_freq)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")

    return fig


def clean_text(text):
    replacements = {
        "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
        "İ": "I", "Ğ": "G", "Ü": "U", "Ş": "S", "Ö": "O", "Ç": "C"
    }

    for tr_char, en_char in replacements.items():
        text = str(text).replace(tr_char, en_char)

    return text


def create_pdf_report(result):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Customer Review Analytics Report", ln=True)

    pdf.ln(5)

    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "1. Summary Table", ln=True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(60, 8, "Metric", border=1)
    pdf.cell(40, 8, "Count", border=1)
    pdf.cell(40, 8, "Percentage", border=1, ln=True)

    pdf.cell(60, 8, "Total Reviews", border=1)
    pdf.cell(40, 8, str(result["total_reviews"]), border=1)
    pdf.cell(40, 8, "-", border=1, ln=True)

    for sentiment, count in result["sentiment_counts"].items():
        percentage = result["sentiment_percentages"].get(sentiment, 0)
        pdf.cell(60, 8, clean_text(sentiment), border=1)
        pdf.cell(40, 8, str(count), border=1)
        pdf.cell(40, 8, f"%{percentage}", border=1, ln=True)

    pdf.ln(8)

    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "2. Category Distribution", ln=True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(80, 8, "Category", border=1)
    pdf.cell(40, 8, "Count", border=1)
    pdf.cell(40, 8, "Percentage", border=1, ln=True)

    for category, count in result["category_counts"].items():
        percentage = round((count / result["total_reviews"]) * 100, 1)
        pdf.cell(80, 8, clean_text(category), border=1)
        pdf.cell(40, 8, str(count), border=1)
        pdf.cell(40, 8, f"%{percentage}", border=1, ln=True)

    pdf.ln(8)

    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "3. Most Frequent Words", ln=True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(80, 8, "Word", border=1)
    pdf.cell(40, 8, "Count", border=1, ln=True)

    for word, count in result["top_words"]:
        pdf.cell(80, 8, clean_text(word), border=1)
        pdf.cell(40, 8, str(count), border=1, ln=True)

    pdf.ln(8)

    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "4. Top Negative Reviews", ln=True)

    pdf.set_font("Arial", "", 10)

    for index, review in enumerate(result["negative_reviews"][:10], start=1):
        pdf.multi_cell(0, 7, f"{index}. {clean_text(review)}")
        pdf.ln(2)

    pdf_output = BytesIO()
    pdf_bytes = pdf.output(dest="S").encode("latin-1", errors="ignore")
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)

    return pdf_output


API_URL = "https://ai-customer-review-api.onrender.com"

st.set_page_config(
    page_title="AI Review Analytics",
    page_icon="💬",
    layout="wide"
)

st.markdown("""
<style>
.main {
    padding-top: 2rem;
}

[data-testid="metric-container"] {
    background-color: #262730;
    border: 1px solid #3c3f58;
    padding: 20px;
    border-radius: 15px;
    text-align: center;
}

[data-testid="metric-container"] label {
    font-size: 18px;
}

.dashboard-card {
    background-color: #ffffff;
    color: #111827;
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.12);
    min-height: 520px;
    margin-bottom: 20px;
}

.dashboard-card h3 {
    color: #111827;
    font-size: 19px;
    margin-bottom: 10px;
}

.card-note {
    color: #4b5563;
    font-size: 14px;
    line-height: 1.6;
}

.highlight-count {
    color: #4f46e5;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.markdown(
    """
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-size: 42px; margin-bottom: 5px;">
            💬 AI-Powered Customer Review Analytics
        </h1>
        <p style="font-size: 16px; color: gray; margin-bottom: 5px;">
            by Sude Hızel
        </p>
        <p style="font-size: 20px; color: #555;">
            Upload customer reviews and instantly generate AI-powered business insights.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("### 1. Upload Review File")
st.write("Please upload an Excel file that contains customer review text.")

uploaded_file = st.file_uploader(
    "Choose an Excel file",
    type=["xlsx"]
)

if uploaded_file is not None:
    if st.button("Analyze Reviews", use_container_width=True):
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        }

        response = requests.post(
            f"{API_URL}/upload_reviews",
            files=files
        )

        result = response.json()

        if "error" in result:
            st.error(result["error"])
        else:
            st.success("File analyzed successfully!")

            sentiment_counts = result["sentiment_counts"]
            sentiment_percentages = result["sentiment_percentages"]
            category_counts = result["category_counts"]

            sentiment_df = pd.DataFrame(
                sentiment_counts.items(),
                columns=["Sentiment", "Count"]
            )

            category_df = pd.DataFrame(
                category_counts.items(),
                columns=["Category", "Count"]
            )

            top_words_df = pd.DataFrame(
                result["top_words"],
                columns=["Word", "Count"]
            )

            st.markdown("---")
            st.markdown("## 📊 Analysis Results")

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)

            kpi1.metric("Total Reviews", result["total_reviews"])
            kpi2.metric(
                "Pozitif",
                sentiment_counts.get("Pozitif", 0),
                f"%{sentiment_percentages.get('Pozitif', 0)}"
            )
            kpi3.metric(
                "Nötr",
                sentiment_counts.get("Nötr", 0),
                f"%{sentiment_percentages.get('Nötr', 0)}"
            )
            kpi4.metric(
                "Negatif",
                sentiment_counts.get("Negatif", 0),
                f"%{sentiment_percentages.get('Negatif', 0)}"
            )

            st.markdown("## 📈 Business Dashboard")

            card1, card2, card3, card4 = st.columns(4)

            with card1:
                st.markdown("### Ana Duygu Dağılımı")

                fig_sentiment = px.pie(
                    sentiment_df,
                    names="Sentiment",
                    values="Count",
                    hole=0.55
                )
                fig_sentiment.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=True
                )
                st.plotly_chart(fig_sentiment, use_container_width=True)

                st.markdown("**Yoğunluk:**")
                st.write(f"Pozitif: {sentiment_counts.get('Pozitif', 0)} adet (%{sentiment_percentages.get('Pozitif', 0)})")
                st.write(f"Nötr: {sentiment_counts.get('Nötr', 0)} adet (%{sentiment_percentages.get('Nötr', 0)})")
                st.write(f"Negatif: {sentiment_counts.get('Negatif', 0)} adet (%{sentiment_percentages.get('Negatif', 0)})")

            with card2:
                st.markdown("### Kategori Kırılımları")

                fig_category = px.bar(
                    category_df,
                    x="Category",
                    y="Count"
                )
                fig_category.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_title="Kategori",
                    yaxis_title="Yorum Sayısı"
                )
                st.plotly_chart(fig_category, use_container_width=True)

                st.markdown("**Yoğunluk:**")
                for _, row in category_df.head(6).iterrows():
                    pct = round((row["Count"] / result["total_reviews"]) * 100, 1)
                    st.write(f"{row['Category']}: {row['Count']} adet (%{pct})")

            with card3:
                st.markdown("### Kelime Yoğunluğu")

                fig_words = px.bar(
                    top_words_df,
                    x="Word",
                    y="Count"
                )
                fig_words.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_title="Kelime",
                    yaxis_title="Kullanım"
                )
                st.plotly_chart(fig_words, use_container_width=True)

                st.markdown("**En sık geçen kelimeler:**")
                for _, row in top_words_df.head(6).iterrows():
                    st.write(f"{row['Word']}: {row['Count']} adet")

            with card4:
                st.markdown("### Öne Çıkan Negatif Yorumlar")

                for review in result["negative_reviews"][:5]:
                    st.warning(review)

            pdf_report = create_pdf_report(result)

            st.download_button(
                label="📄 Analiz Raporunu PDF Olarak İndir",
                data=pdf_report,
                file_name="customer_review_analytics_report.pdf",
                mime="application/pdf",
                use_container_width=True
            )        

            st.markdown("---")
            st.markdown("## ☁️ Word Cloud")

            wordcloud_fig = create_wordcloud(result["top_words"])
            st.pyplot(wordcloud_fig)

            st.subheader("Review Filters")

            selected_sentiment = st.selectbox(
                "Select Sentiment",
                ["All", "Pozitif", "Nötr", "Negatif"]
            )

            st.subheader("Sample Reviews with Sentiment")

            filtered_reviews = result["sample_reviews"]

            if selected_sentiment != "All":
                filtered_reviews = [
                    review
                    for review in filtered_reviews
                    if review["Sentiment"] == selected_sentiment
                ]

            for item in filtered_reviews:
                st.write(f"**{item['Sentiment']}** — {item['Yorum']}")

            st.subheader("Ask Questions About Reviews")

            question = st.text_input(
                "Ask a question",
                placeholder="Örn: En çok hangi konuda şikayet var?"
            )

            if st.button("Ask AI"):
                if question.strip() == "":
                    st.warning("Please write a question.")
                else:
                    question_response = requests.post(
                        f"{API_URL}/ask_reviews",
                        json={"question": question}
                    )

                    answer_result = question_response.json()

                    st.session_state.chat_history.append({
                        "question": question,
                        "answer": answer_result["answer"]
                    })

            if st.session_state.chat_history:
                st.markdown("### Chat History")

                for chat in reversed(st.session_state.chat_history):
                    st.markdown(f"**👤 You:** {chat['question']}")
                    st.markdown(f"**🤖 AI:** {chat['answer']}")
                    st.markdown("---")                        
