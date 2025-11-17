from flask import Flask, jsonify, render_template, request, session, redirect
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash  
from functools import wraps
from helpers import login_required
from google import genai
from google.genai import types
from markupsafe import Markup
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import markdown2
import re

# Charger les variables d'environnement du fichier .env
load_dotenv()

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = os.getenv("SECRET_KEY")
Session(app)

def get_db():
    """Connexion à PostgreSQL/Supabase"""
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

# Les tables sont déjà créées dans Supabase, pas besoin d'init_db()

def markdown_to_html(text):
    """Convertir du Markdown en HTML de manière sécurisée"""
    try:
        # Convertir le Markdown en HTML
        html = markdown2.markdown(text, extras=['tables', 'fenced-code-blocks', 'code-friendly'])
        return Markup(html)
    except Exception as e:
        print(f"Error converting markdown: {str(e)}")
        return Markup(f"<p>{text}</p>")

def get_gemini_response(user_message, conversation_history=None):
    """Obtenir une réponse de Gemini avec l'historique complet de la conversation"""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model = "gemini-flash-lite-latest"
    
    # Construire l'historique complet (CRUCIAL pour la mémoire du chatbot!)
    contents = []
    
    # Ajouter l'historique si disponible
    if conversation_history:
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"  # Gemini utilise "model" au lieu de "assistant"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                )
            )
    
    # Ajouter le message actuel de l'utilisateur
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )
    )
    
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        image_config=types.ImageConfig(image_size="1K"),
        system_instruction=[
            types.Part.from_text(text="""Tu es "Finker", un assistant IA expert en intelligence artificielle et sciences informatiques.
Ta mission est d'enseigner les fondements de l'IA, du machine learning et de la science des données.
- Tu t'appelles Finker et tu te présentes comme tel
- Tu expliques avec clarté, pédagogie et structure
- Tu adaptes ton niveau selon le niveau de l'utilisateur
- Tu illustres tes propos avec des exemples concrets et des analogies du monde réel
- Tu te souviens du contexte complet de la conversation pour des réponses cohérentes
- Tu es amical, pédagogue et encourageant
- Tu fournis des ressources supplémentaires pour approfondir les sujets abordés
- Tu encourages l'utilisateur à poser des questions et à explorer davantage le sujet
-Tu ne te présentes pas pendant trop longtemps et tu ne demandes pas trop d'informations à l'utilisateur"""),
        ],
    )
    
    response_text = ""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        response_text += chunk.text
    
    return response_text

def get_or_create_conversation(user_id, conversation_id=None):
    """Obtenir ou créer une conversation par défaut pour l'utilisateur"""
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if conversation_id:
            # Récupérer la conversation spécifique
            cursor.execute("SELECT id FROM public.conversations WHERE id=%s AND user_id=%s",
                          (conversation_id, user_id))
            conv = cursor.fetchone()
            if conv:
                cursor.close()
                return conv["id"]
        
        # Créer une nouvelle conversation par défaut
        cursor.execute(
            "INSERT INTO public.conversations (user_id, title) VALUES (%s, %s) RETURNING id",
            (user_id, "Nouvelle conversation")
        )
        new_conv = cursor.fetchone()
        conn.commit()
        cursor.close()
        return new_conv["id"]

@app.route("/search", methods=["POST"])
@login_required
def search():
    """Route API pour traiter les messages du chatbot via fetch - SELECT...UPDATE optimisé"""
    user_id = session.get("user_id")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
            
        user_message = data.get("message", "").strip()
        conversation_id = data.get("conversation_id")
        
        if not user_message:
            return jsonify({"error": "Empty message"}), 400
        
        # Obtenir ou créer une conversation
        conversation_id = get_or_create_conversation(user_id, conversation_id)
        
        # ✅ RÉCUPÉRER L'HISTORIQUE COMPLET de la conversation (CRUCIAL!)
        conversation_history = []
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # SELECT l'historique des messages pour cette conversation
            cursor.execute(
                """SELECT role, content FROM public.conversations_history 
                   WHERE conversation_id=%s AND user_id=%s 
                   ORDER BY created_at ASC""",
                (conversation_id, user_id)
            )
            conversation_history = cursor.fetchall()
            cursor.close()
        
        # Stocker le message utilisateur
        with get_db() as conn:
            cursor = conn.cursor()
            
            # INSERT le message utilisateur
            cursor.execute(
                "INSERT INTO public.conversations_history (conversation_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
                (conversation_id, user_id, "user", user_message)
            )
            conn.commit()
        
        # ✅ Obtenir la réponse de Gemini AVEC l'historique complet
        gemini_response = get_gemini_response(user_message, conversation_history)
        
        if not gemini_response or gemini_response.strip() == "":
            return jsonify({"error": "No response from AI"}), 500
        
        # INSERT la réponse + UPDATE only updated_at (metadata)
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # INSERT la réponse AI
            cursor.execute(
                "INSERT INTO public.conversations_history (conversation_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
                (conversation_id, user_id, "assistant", gemini_response)
            )
            
            # UPDATE: just update the timestamp (vérification de propriété incluse)
            cursor.execute('''
                UPDATE public.conversations 
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = %s 
                AND user_id = %s
                RETURNING id, title, updated_at
            ''', (conversation_id, user_id))
            
            updated_conv = cursor.fetchone()
            conn.commit()
            cursor.close()
            
            if not updated_conv:
                return jsonify({"error": "Conversation not found or unauthorized"}), 403
        
        # Convertir la réponse en HTML pour affichage
        response_html = markdown_to_html(gemini_response)
        
        return jsonify({
            "conversation_id": conversation_id,
            "user_message": user_message,
            "assistant_response": gemini_response,
            "assistant_response_html": str(response_html)
        }), 200
    except Exception as e:
        print(f"Error in /search: {str(e)}")
        return jsonify({"error": "Server error: " + str(e)}), 500

@app.route("/", methods=["GET", "POST"])
@login_required
def home():
    user_id = session.get("user_id")
    
    # Récupérer conversation_id depuis l'URL ou créer une nouvelle
    conversation_id = request.args.get('conversation_id', type=int)
    
    # Si pas de conversation_id, créer ou récupérer une conversation par défaut
    if not conversation_id:
        conversation_id = get_or_create_conversation(user_id)
    else:
        # Vérifier que la conversation appartient à l'utilisateur
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT id FROM public.conversations WHERE id=%s AND user_id=%s",
                          (conversation_id, user_id))
            if not cursor.fetchone():
                cursor.close()
                # Si conversation invalide, créer une nouvelle
                conversation_id = get_or_create_conversation(user_id)
            cursor.close()
    
    # Récupérer l'historique des messages (SELECT)
    messages = []
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT role, content FROM public.conversations_history WHERE conversation_id=%s AND user_id=%s ORDER BY created_at ASC",
            (conversation_id, user_id)
        )
        rows = cursor.fetchall()
        cursor.close()
        messages = [
            {"role": row["role"], "content": markdown_to_html(row["content"]) if row["role"] == "assistant" else row["content"]} 
            for row in rows
        ]
    
    # Récupérer toutes les conversations de l'utilisateur (SELECT)
    conversations = []
    username = None
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer le nom d'utilisateur
        cursor.execute("SELECT username FROM public.users WHERE id=%s", (user_id,))
        user_data = cursor.fetchone()
        username = user_data['username'] if user_data else f"User#{user_id}"
        
        # Récupérer les conversations
        cursor.execute(
            "SELECT id, title, updated_at FROM public.conversations WHERE user_id=%s ORDER BY updated_at DESC",
            (user_id,)
        )
        conversations = cursor.fetchall()
        cursor.close()
    
    return render_template("dashboard.html", 
                         messages=messages, 
                         user_id=user_id,
                         username=username,
                         conversation_id=conversation_id,
                         conversations=conversations)

@app.route("/api/conversations", methods=["GET"])
@login_required
def get_conversations():
    """Lister toutes les conversations de l'utilisateur (SELECT)"""
    user_id = session.get("user_id")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT id, title, updated_at FROM public.conversations WHERE user_id=%s ORDER BY updated_at DESC",
                (user_id,)
            )
            conversations = cursor.fetchall()
            cursor.close()
        
        return jsonify(conversations), 200
    except Exception as e:
        print(f"Error in /api/conversations: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/conversations/<int:conversation_id>", methods=["GET"])
@login_required
def get_conversation_messages(conversation_id):
    """Récupérer les messages d'une conversation spécifique (SELECT)"""
    user_id = session.get("user_id")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Vérifier que la conversation appartient à l'utilisateur
            cursor.execute("SELECT id FROM public.conversations WHERE id=%s AND user_id=%s", 
                          (conversation_id, user_id))
            if not cursor.fetchone():
                cursor.close()
                return jsonify({"error": "Conversation not found"}), 404
            
            # Récupérer les messages
            cursor.execute(
                "SELECT role, content, created_at FROM public.conversations_history WHERE conversation_id=%s ORDER BY created_at ASC",
                (conversation_id,)
            )
            messages = cursor.fetchall()
            cursor.close()
        
        # Convertir les messages en HTML
        formatted_messages = [
            {"role": msg["role"], "content": markdown_to_html(msg["content"]) if msg["role"] == "assistant" else msg["content"]} 
            for msg in messages
        ]
        
        return jsonify(formatted_messages), 200
    except Exception as e:
        print(f"Error in /api/conversations/<id>: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/conversations/new", methods=["POST"])
@login_required
def create_conversation():
    """Créer une nouvelle conversation (INSERT)"""
    user_id = session.get("user_id")
    
    try:
        data = request.get_json()
        title = data.get("title", "Nouvelle conversation").strip()
        
        if not title:
            title = "Nouvelle conversation"
        
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "INSERT INTO public.conversations (user_id, title) VALUES (%s, %s) RETURNING id, title, created_at",
                (user_id, title)
            )
            conversation = cursor.fetchone()
            conn.commit()
            cursor.close()
        
        return jsonify(conversation), 201
    except Exception as e:
        print(f"Error in /api/conversations/new: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/conversations/<int:conversation_id>/update", methods=["PUT"])
@login_required
def update_conversation(conversation_id):
    """Renommer une conversation (UPDATE)"""
    user_id = session.get("user_id")
    
    try:
        data = request.get_json()
        new_title = data.get("title", "").strip()
        
        if not new_title:
            return jsonify({"error": "Title cannot be empty"}), 400
        
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Vérifier que la conversation appartient à l'utilisateur
            cursor.execute("SELECT id FROM public.conversations WHERE id=%s AND user_id=%s", 
                          (conversation_id, user_id))
            if not cursor.fetchone():
                cursor.close()
                return jsonify({"error": "Conversation not found"}), 404
            
            # UPDATE le titre
            cursor.execute(
                "UPDATE public.conversations SET title=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s RETURNING id, title",
                (new_title, conversation_id)
            )
            conversation = cursor.fetchone()
            conn.commit()
            cursor.close()
        
        return jsonify(conversation), 200
    except Exception as e:
        print(f"Error in /api/conversations/<id>/update: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/conversations/<int:conversation_id>/delete", methods=["DELETE"])
@login_required
def delete_conversation(conversation_id):
    """Supprimer une conversation et ses messages (DELETE cascade)"""
    user_id = session.get("user_id")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Vérifier que la conversation appartient à l'utilisateur
            cursor.execute("SELECT id FROM public.conversations WHERE id=%s AND user_id=%s", 
                          (conversation_id, user_id))
            if not cursor.fetchone():
                cursor.close()
                return jsonify({"error": "Conversation not found"}), 404
            
            # DELETE la conversation (les messages sont supprimés automatiquement grâce au CASCADE)
            cursor.execute("DELETE FROM public.conversations WHERE id=%s", (conversation_id,))
            conn.commit()
            cursor.close()
        
        return jsonify({"message": "Conversation deleted"}), 200
    except Exception as e:
        print(f"Error in /api/conversations/<id>/delete: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/messages/<int:conversation_id>/delete", methods=["DELETE"])
@login_required
def delete_message(conversation_id):
    """Supprimer un message spécifique (DELETE)"""
    user_id = session.get("user_id")
    
    try:
        data = request.get_json()
        message_id = data.get("message_id")
        
        if not message_id:
            return jsonify({"error": "Message ID required"}), 400
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Vérifier que la conversation appartient à l'utilisateur
            cursor.execute("SELECT id FROM public.conversations WHERE id=%s AND user_id=%s", 
                          (conversation_id, user_id))
            if not cursor.fetchone():
                cursor.close()
                return jsonify({"error": "Conversation not found"}), 404
            
            # DELETE le message
            cursor.execute("DELETE FROM public.conversations_history WHERE id=%s AND conversation_id=%s", 
                          (message_id, conversation_id))
            
            if cursor.rowcount == 0:
                conn.commit()
                cursor.close()
                return jsonify({"error": "Message not found"}), 404
            
            conn.commit()
            cursor.close()
        
        return jsonify({"message": "Message deleted"}), 200
    except Exception as e:
        print(f"Error in /api/messages/<id>/delete: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
@login_required
def dashboard():
    # Rediriger vers la page d'accueil (qui gère tout)
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username or not password or not confirmation:
            error = "Please fill in all fields."
        elif password != confirmation:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif not re.search("[a-z]", password):
            error = "Password must contain at least one lowercase letter."
        elif not re.search("[A-Z]", password):
            error = "Password must contain at least one uppercase letter."
        elif not re.search("[0-9]", password):
            error = "Password must contain at least one number."
        elif not re.search("[#$%^&+!=]", password):
            error = "Password must contain at least one special character."
        else:
            try:
                with get_db() as conn:
                    cursor = conn.cursor()
                    hash_password = generate_password_hash(password)
                    cursor.execute("INSERT INTO public.users (username, password) VALUES (%s, %s)", (username, hash_password))
                    conn.commit()
                    cursor.close()
                return redirect("/login")
            except psycopg2.IntegrityError:
                error = "User already exists."
    return render_template("register.html", error=error, user_id=session.get("user_id"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")
        if not username or not password:
            error = "Please fill in all fields."
        else:
            with get_db() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM public.users WHERE username=%s", (username,))
                user = cursor.fetchone()
                cursor.close()
                if user and check_password_hash(user["password"], password):
                    session["user_id"] = user["id"]
                    return redirect("/")
                else:
                    error = "Invalid credentials."
    return render_template("login.html", error=error, user_id=session.get("user_id"))

@app.route("/pepe")
@login_required
def pepe():
    """Page Pepe Chad"""
    return render_template("pepe.html", user_id=session.get("user_id"))

if __name__ == "__main__":
    app.run(debug=False)