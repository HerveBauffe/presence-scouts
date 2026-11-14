from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, PasswordField
from wtforms.validators import DataRequired, Optional

class AddMemberForm(FlaskForm):
    first_name = StringField("Prénom", validators=[DataRequired()])
    last_name = StringField("Nom de famille", validators=[DataRequired()])
    totem = StringField("Totem (facultatif)", validators=[Optional()])
    submit = SubmitField("Ajouter")

class AddGroupForm(FlaskForm):
    name = StringField("Nom du groupe", validators=[DataRequired()])
    submit = SubmitField("Créer le groupe")

class AddMeetingForm(FlaskForm):
    title = StringField("Titre de la réunion", validators=[DataRequired()])
    date = DateField("Date", validators=[DataRequired()], format="%Y-%m-%d")
    submit = SubmitField("Ajouter la réunion")

class LoginForm(FlaskForm):
    username = StringField("Nom d'utilisateur", validators=[DataRequired()])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    submit = SubmitField("Se connecter")