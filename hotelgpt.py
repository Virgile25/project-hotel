import requests
from bs4 import BeautifulSoup
import pandas as pd
from textblob import TextBlob
import streamlit as st
import matplotlib.pyplot as plt
from supabase import create_client, Client
import os
from fpdf import FPDF
import io

# Configuration de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-supabase-url.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-supabase-api-key")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fonction pour récupérer les avis d'un hôtel depuis Supabase
def get_reviews_from_db(hotel_name):
    response = supabase.table("reviews").select("review_text, rating, sentiment, created_at").eq("hotel_name", hotel_name).execute()
    return response.data if response.data else []

# Fonction pour générer les graphiques et les enregistrer

def generate_charts(df):
    img_paths = []
    
    # Évolution des sentiments
    plt.figure(figsize=(10, 5))
    df['sentiment_moyen'] = df['sentiment'].rolling(window=5, min_periods=1).mean()
    plt.plot(df['created_at'], df['sentiment_moyen'], marker='o', linestyle='-', color='blue')
    plt.xlabel("Date")
    plt.ylabel("Sentiment Moyen")
    plt.title("Évolution du Sentiment des Avis Clients")
    plt.xticks(rotation=45)
    img_path1 = "sentiment_evolution.png"
    plt.savefig(img_path1)
    img_paths.append(img_path1)
    
    # Répartition des notes
    plt.figure()
    df['rating'].value_counts().sort_index().plot(kind='bar', color='skyblue', edgecolor='black')
    plt.xlabel("Note")
    plt.ylabel("Nombre d'Avis")
    plt.title("Distribution des Notes des Avis")
    img_path2 = "rating_distribution.png"
    plt.savefig(img_path2)
    img_paths.append(img_path2)
    
    # Répartition des sentiments
    plt.figure()
    sentiment_labels = ['Négatif', 'Neutre', 'Positif']
    sentiment_counts = [sum(df['sentiment'] < -0.1), sum((df['sentiment'] >= -0.1) & (df['sentiment'] <= 0.1)), sum(df['sentiment'] > 0.1)]
    plt.pie(sentiment_counts, labels=sentiment_labels, autopct='%1.1f%%', colors=['red', 'gray', 'green'])
    plt.title("Répartition des Sentiments")
    img_path3 = "sentiment_distribution.png"
    plt.savefig(img_path3)
    img_paths.append(img_path3)
    
    return img_paths

# Fonction pour générer un rapport PDF avec graphiques
def generate_pdf(hotel_name, reviews, avg_rating, avg_sentiment, total_reviews, df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(200, 10, f"Rapport d'Avis - {hotel_name}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"⭐ Note Moyenne: {avg_rating:.1f}/5", ln=True)
    pdf.cell(200, 10, f"😊 Sentiment Moyen: {avg_sentiment:.2f}", ln=True)
    pdf.cell(200, 10, f"📝 Nombre Total d'Avis: {total_reviews}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(200, 10, "Détail des Avis:", ln=True)
    pdf.set_font("Arial", size=10)
    for review in reviews[:20]:  # Limite à 20 avis pour éviter un PDF trop long
        pdf.multi_cell(0, 10, f"{review['created_at']} - Note: {review['rating']} - Sentiment: {review['sentiment']:.2f}\n{review['review_text']}")
        pdf.ln(5)
    
    # Générer les graphiques
    img_paths = generate_charts(df)
    for img_path in img_paths:
        pdf.add_page()
        pdf.image(img_path, x=10, y=20, w=180)
    
    return pdf

# Interface utilisateur avec Streamlit
st.title("📊 Dashboard d'Analyse des Avis Clients")

hotel_name = st.text_input("🏨 Nom de l'hôtel")

def display_dashboard(hotel_name):
    reviews = get_reviews_from_db(hotel_name)
    if not reviews:
        st.warning("Aucun avis trouvé pour cet hôtel.")
        return
    
    df = pd.DataFrame(reviews)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df.sort_values("created_at", inplace=True)
    
    # Affichage des avis
    st.subheader("📃 Liste des Avis")
    st.dataframe(df[['created_at', 'review_text', 'rating', 'sentiment']])
    
    # Statistiques globales
    st.subheader("📈 Statistiques Globales")
    avg_rating = df['rating'].mean()
    avg_sentiment = df['sentiment'].mean()
    total_reviews = len(df)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("⭐ Note Moyenne", f"{avg_rating:.1f}/5")
    col2.metric("😊 Score de Sentiment Moyen", f"{avg_sentiment:.2f}")
    col3.metric("📝 Nombre Total d'Avis", total_reviews)
    
    # Bouton pour générer le rapport PDF
    if st.button("📤 Exporter en PDF"):
        pdf = generate_pdf(hotel_name, reviews, avg_rating, avg_sentiment, total_reviews, df)
        pdf_output = io.BytesIO()
        pdf.output(pdf_output, 'F')
        pdf_output.seek(0)
        st.download_button(label="📄 Télécharger le Rapport PDF", data=pdf_output, file_name=f"Rapport_Avis_{hotel_name}.pdf", mime="application/pdf")

if st.button("📊 Générer le Dashboard"):
    if hotel_name:
        display_dashboard(hotel_name)
    else:
        st.error("Veuillez entrer un nom d'hôtel.")
