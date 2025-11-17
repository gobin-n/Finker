# 🤖 Chatbot IA - Flask Multi-Conversations

Une application Flask complète avec support **multi-conversations par utilisateur**, authentification sécurisée, et intégration **Google Gemini AI**. Conçue pour fonctionner avec **PostgreSQL/Supabase**.

---

## ✨ Fonctionnalités

✅ **Authentification & Sessions**
- Inscription/Connexion sécurisée (hachage des mots de passe)
- Gestion des sessions utilisateur

✅ **Multi-Conversations**
- Créer, renommer, supprimer des conversations
- Basculer entre plusieurs conversations
- Historique complet des messages par conversation

✅ **Intégration Gemini AI**
- Réponses en temps réel avec Google Gemini Flash
- Support du Markdown dans les réponses

✅ **Interface Dashboard**
- Sidebar avec liste des conversations
- Chat en temps réel via AJAX
- Gestion intuitive des conversations

✅ **Base de Données PostgreSQL**
- Prête pour Supabase
- Transactions ACID
- Indexes pour performance optimale

---

## 🏗️ Architecture

```
chatbot-ia/
├── main.py                      # Application Flask principale
├── helpers.py                   # Utilitaires (login_required, etc)
├── requirements.txt             # Dépendances Python
├── templates/
│   ├── dashboard.html          # Interface principale
│   ├── login.html              # Page de connexion
│   ├── register.html           # Page d'inscription
│   └── layout.html             # Template de base
├── test_db.py                  # Tests de la base de données
├── query_examples.py           # Exemples de requêtes SQL
└── api_client_examples.py      # Exemples d'utilisation API
```

### Stack Technique
- **Backend**: Flask (Python)
- **Base de Données**: PostgreSQL / Supabase
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **IA**: Google Gemini Flash API
- **Authentification**: Werkzeug (hachage sécurisé)

---

## 🚀 Installation

### Prérequis
- Python 3.9+
- PostgreSQL/Supabase
- Clé API Google Gemini
- Git

### Étape 1: Cloner le projet
```bash
git clone <votre-repo>
cd chatbot-ia
```

### Étape 2: Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate      # Windows
```

### Étape 3: Installer les dépendances
```bash
pip install -r requirements.txt
```

### Étape 4: Configurer les variables d'environnement
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

---

## ⚙️ Configuration

### `.env` - Variables d'environnement

```bash
# Clé secrète Flask (générer avec: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=votre-clé-secrète-ici

# Clé API Google Gemini
GEMINI_API_KEY=votre-clé-gemini-ici

# URL de connexion PostgreSQL
# Format: postgresql://user:password@host:port/database
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db

# Environnement
FLASK_ENV=development
```

### Obtenir les clés

**Google Gemini API:**
1. Aller sur [Google AI Studio](https://aistudio.google.com)
2. Créer une nouvelle clé API
3. Copier la clé dans `GEMINI_API_KEY`

**Supabase (Alternative PostgreSQL):**
1. Créer un compte sur [Supabase](https://supabase.com)
2. Créer un nouveau projet
3. Copier l'URL de connexion PostgreSQL dans `DATABASE_URL`

---

## 🎯 Démarrage

### Mode Développement
```bash
python main.py
```

L'application est accessible sur `http://localhost:5000`

### Mode Production
```bash
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

---

## 📡 API Endpoints

### Authentification

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET/POST` | `/login` | Page de connexion |
| `GET/POST` | `/register` | Page d'inscription |
| `GET` | `/logout` | Déconnexion |

### Conversations (READ)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/conversations` | Lister toutes les conversations |
| `GET` | `/api/conversations/<id>` | Récupérer les messages d'une conversation |

### Conversations (CREATE/UPDATE/DELETE)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/conversations/new` | Créer une conversation |
| `PUT` | `/api/conversations/<id>/update` | Renommer une conversation |
| `DELETE` | `/api/conversations/<id>/delete` | Supprimer une conversation |

### Messages

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/search` | Envoyer un message et obtenir une réponse IA |
| `DELETE` | `/api/messages/<conversation_id>/delete` | Supprimer un message |

---

## 🗄️ Schéma Base de Données

### Table: `users`
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table: `conversations`
```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT 'Nouvelle conversation',
    current_context TEXT DEFAULT '',
    last_message TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
```

### Table: `conversations_history`
```sql
CREATE TABLE conversations_history (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_history_conversation_id ON conversations_history(conversation_id);
CREATE INDEX idx_history_user_id ON conversations_history(user_id);
```

---

## 💡 Exemples d'Utilisation

### 1️⃣ Récupérer toutes les conversations
```javascript
// JavaScript
fetch('/api/conversations')
    .then(res => res.json())
    .then(conversations => console.log(conversations));
```

```python
# Python
import requests
response = requests.get('http://localhost:5000/api/conversations', 
                       cookies={'session': 'your-session-id'})
print(response.json())
```

### 2️⃣ Créer une conversation
```javascript
fetch('/api/conversations/new', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({title: 'Ma nouvelle conversation'})
})
.then(res => res.json())
.then(conv => console.log('Créée:', conv));
```

### 3️⃣ Envoyer un message
```javascript
fetch('/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        message: 'Explique-moi le machine learning',
        conversation_id: 1
    })
})
.then(res => res.json())
.then(data => console.log(data.assistant_response));
```

### 4️⃣ Renommer une conversation
```javascript
fetch('/api/conversations/1/update', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({title: 'Machine Learning Basics'})
})
.then(res => res.json())
.then(conv => console.log('Renommée:', conv));
```

### 5️⃣ Supprimer une conversation
```javascript
fetch('/api/conversations/1/delete', {method: 'DELETE'})
.then(res => res.json())
.then(data => console.log(data.message));
```

---

## 🔄 Opérations SELECT...UPDATE

Les opérations **SELECT...UPDATE** combinent une sélection avec une mise à jour en une seule requête SQL.

### Exemple: Mise à jour du contexte courant
```python
def update_conversation_context(user_id, conversation_id, new_message, ai_response):
    """Mettre à jour le contexte courant d'une conversation"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # UPDATE avec vérification de propriété
        cursor.execute('''
            UPDATE conversations 
            SET 
                current_context = CONCAT(current_context, %s, '\\n---\\n'),
                last_message = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s 
            AND user_id = %s
            RETURNING id, title, updated_at
        ''', (
            f"User: {new_message}\nAI: {ai_response}",
            ai_response,
            conversation_id,
            user_id
        ))
        
        result = cursor.fetchone()
        conn.commit()
        
        return {"success": True, "data": result} if result else {"success": False, "error": "Unauthorized"}
    finally:
        cursor.close()
        conn.close()
```

### Exemple: UPDATE avec JOIN
```python
def update_messages_by_conversation(conversation_id):
    """Marquer tous les messages comme traités"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE conversations_history 
            SET role = 'processed'
            WHERE conversation_id = %s
            RETURNING id
        ''', (conversation_id,))
        
        result = cursor.fetchall()
        conn.commit()
        
        return {"updated": len(result)}
    finally:
        cursor.close()
        conn.close()
```

---

## 🌐 Déploiement Supabase

### Étape 1: Créer un projet Supabase
1. Aller sur [supabase.com](https://supabase.com)
2. Cliquer sur "New Project"
3. Remplir les détails (nom, mot de passe BD, région)
4. Attendre l'initialisation

### Étape 2: Récupérer les informations de connexion
1. Aller dans "Settings" → "Database"
2. Copier l'URL de connexion PostgreSQL
3. Copier le mot de passe BD

### Étape 3: Configurer DATABASE_URL
```bash
# Format Supabase
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

### Étape 4: Exécuter les migrations
```bash
python main.py  # Les tables se créent automatiquement
```

### Étape 5: Vérifier la connexion
```bash
python test_db.py
```

---

## 🧪 Tests

### Tester la connexion à la BD
```bash
python test_db.py
```

### Voir les exemples de requêtes
```bash
cat query_examples.py
```

### Utiliser le client API
```bash
python api_client_examples.py
```

---

## 🐛 Dépannage

### Erreur: "psycopg2.OperationalError: could not connect to server"
**Solution**: Vérifier que:
1. PostgreSQL/Supabase est en ligne
2. `DATABASE_URL` est correct dans `.env`
3. Les credentials (user/password) sont valides

```bash
# Tester la connexion
psql postgresql://user:password@host:5432/database
```

### Erreur: "ImportError: No module named 'psycopg2'"
**Solution**: Installer les dépendances
```bash
pip install -r requirements.txt
```

### Erreur: "GEMINI_API_KEY not found"
**Solution**: Ajouter la clé dans `.env`
```bash
GEMINI_API_KEY=sk-...your-key...
```

### Les conversations ne s'affichent pas
**Solution**: Vérifier que:
1. Vous êtes connecté (session valide)
2. Les tables existent: `python test_db.py`
3. Les indexes sont créés

---

## 📚 Fichiers Importants

| Fichier | Description |
|---------|-------------|
| `main.py` | Application Flask principale |
| `helpers.py` | Décorateur `@login_required` |
| `test_db.py` | Tests de base de données |
| `query_examples.py` | Exemples de requêtes SQL |
| `api_client_examples.py` | Client API avec exemples |
| `templates/dashboard.html` | Interface du chatbot |

---

## 🔐 Sécurité

✅ **Meilleures pratiques implémentées:**
- Hachage des mots de passe (Werkzeug)
- Protection CSRF (session Flask)
- Vérification de propriété des ressources
- Paramètres liés (prévention SQL injection)
- Transactions ACID pour intégrité des données

---

## 📝 Variables d'Environnement

```bash
SECRET_KEY                  # Clé secrète Flask (32 bytes hex)
GEMINI_API_KEY             # Clé API Google Gemini
DATABASE_URL               # URL PostgreSQL (postgresql://...)
FLASK_ENV                  # development / production
```

**Générer une clé secrète:**
```python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🚢 Production

### Avec Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

### Avec Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "main:app"]
```

---

**Dernière mise à jour**: Novembre 2025

4. **Lancer l'application**
```bash
python3 main.py
```

L'app sera disponible sur `http://localhost:5000`

## 🔑 Concepts clés expliqués

### 1. **Secret Key (clé secrète)**
- Utilisée pour signer les **sessions** Flask
- Doit être **unique** et **complexe** pour la sécurité
- Ne doit **jamais** être partagée publiquement
- Générée aléatoirement et stockée dans `.env`

### 2. **Hachage des mots de passe**
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Enregistrement
hash_password = generate_password_hash(password)  # Génère un hash unique

# Connexion
check_password_hash(hash_password, user_password)  # Compare les hashes
```
- Les mots de passe ne sont **jamais** stockés en clair
- Chaque mot de passe génère un hash différent

### 3. **Authentification et sessions**
- `@login_required` : Décorateur qui force l'authentification
- `session["user_id"]` : Stocke l'ID utilisateur de manière sécurisée
- Flask-Session : Stockage des sessions en fichiers ou base de données

### 4. **Markdown support**
- Les réponses Gemini sont converties **Markdown → HTML**
- Permet le formatage : **gras**, *italique*, listes, code, tableaux, etc.
- Fonction `markdown_to_html()` utilise `markdown2`

### 5. **Architecture des tables**

**Table `users`**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
```

**Table `messages`**
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,  -- "user" ou "assistant"
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
```

## 🚀 Utilisation

### S'inscrire
1. Aller sur `http://localhost:5000/register`
2. Entrer un nom d'utilisateur et mot de passe
3. Confirmer le mot de passe
4. Se connecter

### Discuter avec le chatbot
1. Aller sur le dashboard après connexion
2. Taper un message dans le formulaire
3. Le message est envoyé via **Fetch API** (sans rechargement)
4. La réponse Gemini s'affiche avec le **formatage Markdown**
5. L'historique est conservé

### Se déconnecter
- Cliquer sur le bouton **"Logout"**
- La session est effacée

## 📁 Structure du projet

```
chatbot-ia/
├── main.py                    # Application Flask principale
├── api.py                     # Logique Gemini (optionnel)
├── helpers.py                 # Décorateur login_required
├── requirements.txt           # Dépendances Python
├── .env                       # Variables d'environnement (NE PAS VERSIONNER)
├── .gitignore                 # Fichiers à ignorer dans Git
├── users.db                   # Base de données SQLite
├── flask_session/             # Données de sessions Flask
└── templates/
    ├── layout.html            # Layout de base avec navbar
    ├── login.html             # Page de connexion
    ├── register.html          # Page d'inscription
    └── dashboard.html         # Page du chat avec Markdown
```

## 🔒 Sécurité

- ✅ Mots de passe hashés avec Werkzeug
- ✅ Sessions sécurisées avec flask_session
- ✅ Clé secrète complexe en variable d'environnement
- ✅ Protection contre l'injection XSS (Jinja2 auto-escape)
- ✅ CORS basique (à améliorer en production)

**À améliorer en production :**
- HTTPS obligatoire
- CSRF tokens
- Rate limiting
- Validation plus stricte des entrées

## 🚀 Migration vers une DB distante (Supabase, PostgreSQL)

Pour passer de SQLite à PostgreSQL/Supabase :

1. Installer `psycopg2` : `pip install psycopg2-binary`
2. Remplacer la fonction `get_db()` pour utiliser PostgreSQL
3. Adapter les requêtes SQL (syntaxe identique généralement)

Exemple avec Supabase :
```python
import psycopg2

def get_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn
```

## 📊 Améliorations futures

- [ ] Migrer vers PostgreSQL/Supabase
- [ ] Ajouter des thèmes (clair/sombre)
- [ ] Suppression/édition de messages
- [ ] Export de conversations en PDF
- [ ] Partage de conversations
- [ ] Multiple IA providers (OpenAI, Claude, etc.)
- [ ] Dashboard admin
- [ ] Pagination de l'historique

## 🐛 Troubleshooting

### Erreur : `ModuleNotFoundError: No module named 'markdown2'`
```bash
python3 -m pip install markdown2
```

### Erreur : `SECRET_KEY not found`
Vérifier que le fichier `.env` existe et contient `SECRET_KEY=...`

### Erreur : `GEMINI_API_KEY not found`
1. Générer une clé sur https://aistudio.google.com/apikey
2. L'ajouter au fichier `.env`

### La DB n'est pas créée
La DB se crée automatiquement au premier lancement. Vérifier les permissions du répertoire.

## 📚 Ressources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Google Gemini API](https://ai.google.dev/)
- [Markdown2](https://github.com/trentm/python-markdown2)
- [Werkzeug Security](https://werkzeug.palletsprojects.com/security/)
- [Bootstrap 5](https://getbootstrap.com/)

## 📝 Licence

Libre d'utilisation. Créé à titre d'exemple pédagogique.

---

**Créé avec ❤️ pour apprendre Flask et l'IA**
