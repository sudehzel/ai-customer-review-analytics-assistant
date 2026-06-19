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
    pdf.cell(0, 10, "AI Customer Review Analytics Report", ln=True)

    pdf.ln(5)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Total Reviews: {result['total_reviews']}", ln=True)

    pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "Sentiment Summary", ln=True)

    pdf.set_font("Arial", "", 12)

    for sentiment, count in result["sentiment_counts"].items():
        percentage = result["sentiment_percentages"].get(sentiment, 0)
        pdf.cell(0, 8, f"{clean_text(sentiment)}: {count} (%{percentage})", ln=True)

    pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "Category Distribution", ln=True)

    pdf.set_font("Arial", "", 12)

    for category, count in result["category_counts"].items():
        pdf.cell(0, 8, f"{clean_text(category)}: {count}", ln=True)

    pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "AI Summary", ln=True)

    pdf.set_font("Arial", "", 11)

    summary_text = clean_text(result["ai_summary"])
    pdf.multi_cell(0, 7, summary_text)

    pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "Top Negative Reviews", ln=True)

    pdf.set_font("Arial", "", 10)

    for review in result["negative_reviews"]:
        pdf.multi_cell(0, 6, "- " + clean_text(review))
        pdf.ln(2)

    pdf_output = BytesIO()
    pdf_bytes = pdf.output(dest="S").encode("latin-1", errors="ignore")
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)

    return pdf_output


API_URL = "http://api:8000"

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

            st.markdown("---")
            st.markdown("## 📊 Analysis Results")

            st.metric("Total Reviews", result["total_reviews"])

            sentiment_counts = result["sentiment_counts"]
            sentiment_percentages = result["sentiment_percentages"]
            category_counts = result["category_counts"]

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Pozitif",
                sentiment_counts.get("Pozitif", 0),
                f"%{sentiment_percentages.get('Pozitif', 0)}"
            )

            col2.metric(
                "Nötr",
                sentiment_counts.get("Nötr", 0),
                f"%{sentiment_percentages.get('Nötr', 0)}"
            )

            col3.metric(
                "Negatif",
                sentiment_counts.get("Negatif", 0),
                f"%{sentiment_percentages.get('Negatif', 0)}"
            )

            st.markdown("## 🤖 AI Business Summary")
            st.info(result["ai_summary"])
            st.subheader("AI Action Plan")
            st.success(result["ai_action_plan"])

            pdf_report = create_pdf_report(result)

            st.download_button(
                label="Download PDF Report",
                data=pdf_report,
                file_name="customer_review_analytics_report.pdf",
                mime="application/pdf"
            )

            st.markdown("---")
            st.markdown("## 📈 Analytics Dashboard")

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

            dash_col1, dash_col2 = st.columns(2)

            with dash_col1:
                st.markdown("### Sentiment Distribution")
                st.dataframe(sentiment_df, use_container_width=True)

                fig_sentiment = px.pie(
                    sentiment_df,
                    names="Sentiment",
                    values="Count",
                    hole=0.45,
                    title="Sentiment Distribution"
                )

                st.plotly_chart(fig_sentiment, use_container_width=True)

            with dash_col2:
                st.markdown("### Category Distribution")
                st.dataframe(category_df, use_container_width=True)

                fig_category = px.pie(
                    category_df,
                    names="Category",
                    values="Count",
                    hole=0.45,
                    title="Category Distribution"
                )

                st.plotly_chart(fig_category, use_container_width=True)

            dash_col3, dash_col4 = st.columns(2)

            with dash_col3:
                st.markdown("### Most Frequent Words")
                st.dataframe(top_words_df, use_container_width=True)
                st.bar_chart(top_words_df.set_index("Word"))

                wordcloud_fig = create_wordcloud(result["top_words"])
                st.pyplot(wordcloud_fig)

            with dash_col4:
                st.markdown("### Top Negative Reviews")
                for review in result["negative_reviews"]:
                    st.error(review)

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
