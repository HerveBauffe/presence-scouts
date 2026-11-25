from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager

# Statuts de présence : source unique pour les routes et les templates.
# Les clés "present" et "excused" sont celles déjà stockées en base. L'ancienne
# clé "absent" (avant les 4 statuts) est lue comme "unexcused", voir normalize_status.
STATUSES = [
    {
        "key": "present", "label": "Présent", "emoji": "✅",
        "btn": "border-green-600 text-green-600 peer-checked:bg-green-600",
        "cell": "bg-green-100 text-green-800",
    },
    {
        "key": "excused", "label": "Absent (excusé)", "emoji": "🙏",
        "btn": "border-yellow-500 text-yellow-600 peer-checked:bg-yellow-500",
        "cell": "bg-yellow-100 text-yellow-800",
    },
    {
        "key": "unexcused", "label": "Absent (non excusé)", "emoji": "⚠️",
        "btn": "border-orange-500 text-orange-600 peer-checked:bg-orange-500",
        "cell": "bg-orange-100 text-orange-800",
    },
    {
        "key": "unwarned", "label": "Absent (pas prévenu)", "emoji": "❌",
        "btn": "border-red-700 text-red-700 peer-checked:bg-red-700",
        "cell": "bg-red-100 text-red-800",
    },
]
STATUS_KEYS = [s["key"] for s in STATUSES]
ABSENT_KEYS = {"excused", "unexcused", "unwarned"}

def normalize_status(value):
    """Renvoie une clé de STATUSES valide, ou None si la valeur est inconnue."""
    if value == "absent":  # ancien statut unique d'absence
        return "unexcused"
    return value if value in STATUS_KEYS else None

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    members = db.relationship("Member", backref="group", lazy=True)

    def __repr__(self):
        return f"<Group {self.name}>"

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    # surnom scout, optionnel : tout le monde n'en a pas
    totem = db.Column(db.String(120), nullable=True)
    # nullable : un membre peut ne pas avoir de groupe
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)

    @property
    def display_name(self):
        """Nom affiché : le totem s'il existe, sinon le prénom."""
        return self.totem if self.totem else self.first_name

    def __repr__(self):
        return f"<Member {self.last_name} {self.first_name}>"

# Utilisateur "staff" unique (non stocké en DB)
class User(UserMixin):
    id = 1
    username = "Staff"
    # change le mot de passe par défaut ici avant de déployer
    password_hash = generate_password_hash("CHANGE THIS PASSWORD")

    @classmethod
    def authenticate(cls, username, password):
        if username == cls.username and check_password_hash(cls.password_hash, password):
            return cls()
        return None
    
class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False,)
    attendances = db.relationship("Attendance", backref="meeting", lazy=True)
    def __repr__(self):
        return f"<Meeting {self.title} on {self.date}>"
    
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meeting.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    # clés de STATUSES : present / excused / unexcused / unwarned (ancien "absent" toléré)
    # pas de ligne = statut non défini (jamais saisi)
    status = db.Column(db.String(20), nullable=True)

    def __repr__(self):
        return f"<Attendance Member {self.member_id} for Meeting {self.meeting_id}: {self.status}>"

@login_manager.user_loader
def load_user(user_id):
    if str(user_id) == "1":
        return User()
    return None
