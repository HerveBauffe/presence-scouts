import os
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from . import db
from .models import (
    Member, User, Meeting, Attendance, Group,
    STATUSES, STATUS_KEYS, ABSENT_KEYS, DEFAULT_ABSENCE, normalize_status,
)
from .forms import AddMemberForm, AddMeetingForm, AddGroupForm, LoginForm

bp = Blueprint("main", __name__)

# Accueil : tableau membres x réunions + résumé par réunion (login requis, sinon page de connexion)
@bp.route("/")
@login_required
def landing():
    # plus récentes d'abord, aussi bien pour les cartes que pour les colonnes du tableau
    meetings = Meeting.query.order_by(Meeting.date.desc(), Meeting.id.desc()).all()
    members = Member.query.order_by(Member.last_name, Member.first_name).all()

    # (member_id, meeting_id) -> statut normalisé
    attendance = {}
    for a in Attendance.query.all():
        status = normalize_status(a.status)
        if status:
            attendance[(a.member_id, a.meeting_id)] = status

    # résumé des présences par réunion
    summaries = {meeting.id: {key: 0 for key in STATUS_KEYS} for meeting in meetings}
    for (member_id, meeting_id), status in attendance.items():
        if meeting_id in summaries:
            summaries[meeting_id][status] += 1

    # une ligne par membre ; case vide (None) = présence jamais saisie, non comptée comme absence
    rows = []
    for member in members:
        cells = [attendance.get((member.id, meeting.id)) for meeting in meetings]
        absences = sum(1 for status in cells if status in ("unexcused", "unwarned"))
        rows.append({"member": member, "cells": cells, "absences": absences})
    # tri stable : le plus d'absences en haut, ordre alphabétique en cas d'égalité
    rows.sort(key=lambda row: -row["absences"])

    return render_template(
        "home.html",
        meetings=meetings,
        rows=rows,
        summaries=summaries,
        statuses=STATUSES,
        status_map={s["key"]: s for s in STATUSES},
    )

# Login
@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)
        if user:
            login_user(user, remember=True)
            flash("Connecté avec succès", "success")
            return redirect(url_for("main.landing"))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect", "danger")
        
    return render_template("login.html", form=form)

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Déconnecté", "info")
    return redirect(url_for("main.landing"))

# Admin : affiche membres + statut des uploads + form d'ajout simple
@bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    form = AddMemberForm()
    if form.validate_on_submit():
        first_name = form.first_name.data.strip()
        last_name = form.last_name.data.strip()
        totem = (form.totem.data or "").strip() or None
        if not Member.query.filter_by(first_name=first_name, last_name=last_name).first():
            db.session.add(Member(first_name=first_name, last_name=last_name, totem=totem))
            db.session.commit()
            flash("Membre ajouté", "success")
            return redirect(url_for("main.admin"))
        else:
            flash("Un membre avec ce nom existe déjà", "warning")

    # formulaire pour groupes
    group_form = AddGroupForm()
    if group_form.validate_on_submit() and "add_group" in request.form:
        name = group_form.name.data.strip()
        if not Group.query.filter_by(name=name).first():
            max_position = db.session.query(db.func.max(Group.position)).scalar() or 0
            db.session.add(Group(name=name, position=max_position + 1))
            db.session.commit()
            flash("Groupe créé", "success")
        else:
            flash("Un groupe portant ce nom existe déjà", "warning")
        return redirect(url_for("main.admin"))

    # formulaire pour réunions
    meeting_form = AddMeetingForm()
    if meeting_form.validate_on_submit() and "add_meeting" in request.form:
        meeting = Meeting(title=meeting_form.title.data, date=meeting_form.date.data)
        db.session.add(meeting)
        db.session.commit()
        flash("Réunion créée", "success")
        return redirect(url_for("main.admin"))

    members = Member.query.order_by(Member.last_name).all()

    # liste des groupes, dans l'ordre choisi par l'utilisateur
    groups = Group.query.order_by(Group.position).all()

    # liste des réunions
    meetings = Meeting.query.order_by(Meeting.date.desc()).all()

    return render_template(
        "admin.html",
        members=members,
        form=form,
        groups=groups,
        group_form=group_form,
        meetings=meetings,
        meeting_form=meeting_form,
    )


# Déplacer un groupe dans l'ordre d'affichage (haut/bas)
@bp.route("/admin/move_group/<int:group_id>/<direction>", methods=["POST"])
@login_required
def move_group(group_id, direction):
    groups = Group.query.order_by(Group.position).all()
    idx = next((i for i, g in enumerate(groups) if g.id == group_id), None)
    if idx is None:
        return redirect(url_for("main.admin"))

    if direction == "up" and idx > 0:
        groups[idx].position, groups[idx - 1].position = groups[idx - 1].position, groups[idx].position
    elif direction == "down" and idx < len(groups) - 1:
        groups[idx].position, groups[idx + 1].position = groups[idx + 1].position, groups[idx].position

    db.session.commit()
    return redirect(url_for("main.admin"))


# Renommer un groupe
@bp.route("/admin/edit_group/<int:group_id>", methods=["POST"])
@login_required
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)
    new_name = (request.form.get("name") or "").strip()
    if not new_name:
        flash("Le nom du groupe ne peut pas être vide", "danger")
        return redirect(url_for("main.admin"))
    existing = Group.query.filter_by(name=new_name).first()
    if existing and existing.id != group.id:
        flash("Un groupe portant ce nom existe déjà", "warning")
        return redirect(url_for("main.admin"))
    group.name = new_name
    db.session.commit()
    flash("Groupe renommé", "success")
    return redirect(url_for("main.admin"))


# Supprimer un groupe (les membres deviennent "sans groupe")
@bp.route("/admin/delete_group/<int:group_id>", methods=["POST"])
@login_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    for member in group.members:
        member.group_id = None
    db.session.delete(group)
    db.session.commit()
    flash("Groupe supprimé", "info")
    return redirect(url_for("main.admin"))


# Modifier en une fois le prénom, nom, totem et groupe de tous les membres
@bp.route("/admin/update_members", methods=["POST"])
@login_required
def update_members():
    members = Member.query.all()
    errors = False

    for m in members:
        first_name = request.form.get(f"first_name_{m.id}")
        last_name = request.form.get(f"last_name_{m.id}")
        totem = request.form.get(f"totem_{m.id}")
        group_id = request.form.get(f"group_id_{m.id}")

        # champs absents = ligne non présente dans le formulaire, on l'ignore
        if first_name is None and last_name is None and totem is None and group_id is None:
            continue

        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        if not first_name or not last_name:
            errors = True
            continue

        m.first_name = first_name
        m.last_name = last_name
        m.totem = (totem or "").strip() or None
        m.group_id = int(group_id) if group_id else None

    db.session.commit()
    if errors:
        flash("Certains membres n'ont pas été mis à jour (prénom/nom manquant)", "warning")
    else:
        flash("Membres mis à jour", "success")
    return redirect(url_for("main.admin"))


# Supprimer un membre (et ses métadonnées en DB)
@bp.route("/admin/delete_member/<int:member_id>", methods=["POST"])
@login_required
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    # supprime aussi les présences liées à ce membre pour éviter les orphelins
    Attendance.query.filter_by(member_id=member.id).delete()
    db.session.delete(member)
    db.session.commit()
    flash("Membre supprimé", "info")
    return redirect(url_for("main.admin"))

# Supprimer une réunion (et ses présences)
@bp.route("/admin/delete_meeting/<int:meeting_id>", methods=["POST"])
@login_required
def delete_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    Attendance.query.filter_by(meeting_id=meeting.id).delete()
    db.session.delete(meeting)
    db.session.commit()
    flash("Réunion supprimée", "info")
    return redirect(url_for("main.admin"))

# Modifier une réunion (titre, date)
@bp.route("/admin/edit_meeting/<int:meeting_id>", methods=["POST"])
@login_required
def edit_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    new_title = request.form.get("title")
    new_date = request.form.get("date")
    if new_title:
        meeting.title = new_title
    if new_date:
        try:
            meeting.date = datetime.strptime(new_date, "%Y-%m-%d")
        except ValueError:
            flash("Format de date invalide", "danger")
            return redirect(url_for("main.admin"))
    db.session.commit()
    flash("Réunion modifiée", "success")
    return redirect(url_for("main.admin"))


# Détail d'une réunion : liste des membres + formulaire de présence
@bp.route("/meetings/<int:meeting_id>", methods=["GET", "POST"])
@login_required
def meeting_detail(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    members = Member.query.order_by(Member.first_name, Member.last_name).all()

    if request.method == "POST":
        for m in members:
            status_value = request.form.get(f"member_{m.id}")
            attendance = Attendance.query.filter_by(meeting_id=meeting.id, member_id=m.id).first()
            if not attendance:
                attendance = Attendance(meeting_id=meeting.id, member_id=m.id)
                db.session.add(attendance)

            # 4 états possibles (voir STATUSES dans models.py)
            if status_value in STATUS_KEYS:
                attendance.status = status_value
            else:
                attendance.status = DEFAULT_ABSENCE  # aucun choix : absence par défaut

        db.session.commit()
        flash("Présences mises à jour", "success")
        return redirect(url_for("main.meeting_detail", meeting_id=meeting.id))

    # Prépare l’état actuel pour précocher (l'ancien statut "absent" est converti)
    attendance_map = {}
    for a in Attendance.query.filter_by(meeting_id=meeting.id).all():
        status = normalize_status(a.status)
        if status:
            attendance_map[a.member_id] = status

    # Regroupe les membres par groupe, les sans-groupe en dernier
    groups = Group.query.order_by(Group.position).all()
    grouped_members = []
    for group in groups:
        group_members = [m for m in members if m.group_id == group.id]
        if group_members:
            grouped_members.append({"id": group.id, "name": group.name, "members": group_members})
    ungrouped = [m for m in members if m.group_id is None]
    if ungrouped:
        grouped_members.append({"id": 0, "name": "Sans groupe", "members": ungrouped})

    return render_template(
        "meeting_detail.html",
        meeting=meeting,
        members=members,
        grouped_members=grouped_members,
        attendance_map=attendance_map,
        statuses=STATUSES,
    )


# Ancienne page "Réunions", désormais fusionnée dans l'Accueil (garde les anciens favoris valides)
@bp.route("/meetings")
@login_required
def meetings_list():
    return redirect(url_for("main.landing"))

@bp.route("/docs/<path:filename>")
def docs(filename):
    docs_dir = os.path.join(current_app.root_path, "docs")
    return send_from_directory(docs_dir, filename)