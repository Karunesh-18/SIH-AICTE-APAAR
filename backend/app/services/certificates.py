"""Certificate record: mint a signed CERTIFICATE token for one student record (a write, audited)."""
import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import settings
from app.domain.apaar import mask
from app.models.certificate import CertificateToken
from app.models.org import Institution, Programme
from app.models.student import StudentRecord
from app.models.user import User
from app.services import audit, signing
from app.services.access import can_access_institution
from app.services.errors import Conflict, Forbidden, NotFound

PURPOSE = "CERTIFICATE"


def issue(db: Session, user: User, record_id: str) -> dict:
    rec = db.get(StudentRecord, record_id)
    if rec is None:
        raise NotFound("Record not found")
    prog = db.get(Programme, rec.programme_id)
    inst = db.get(Institution, prog.institution_id)
    if not can_access_institution(db, user, inst):
        raise Forbidden("You do not have access to this record")
    if not rec.apaar_id or rec.status == "withdrawn" or not rec.is_current:
        raise Conflict("Only a current record with an APAAR ID can have a certificate view")
    # student_id: the model has no enrolment number, so the record id is the closest identifier.
    fields = {"institution": inst.name, "name": rec.name, "apaar_id": rec.apaar_id,
              "student_id": rec.id, "programme": prog.name, "year_of_study": rec.year_of_study}
    now = clock.now()
    jti, exp = str(uuid.uuid4()), now + timedelta(days=settings.certificate_token_days)
    token = signing.sign({"jti": jti, "sub": mask(rec.apaar_id), "purpose": PURPOSE,
                          "fields": fields, "iat": now, "exp": exp, "iss": settings.verify_issuer})
    db.add(CertificateToken(record_id=rec.id, token_jti=jti, issued_by=user.id,
                            issued_at=now, expires_at=exp))
    audit.append(db, actor_id=user.id, actor_role=user.role, action="CERTIFICATE.ISSUED",
                 entity_type="student_record", entity_id=rec.id,
                 after={"jti": jti, "expires_at": exp.isoformat(), "apaar_id": mask(rec.apaar_id)})
    return {"token": token, "fields": fields, "issued_at": now, "expires_at": exp,
            "qr_url": f"{settings.public_base_url.rstrip('/')}/verify/{token}"}
