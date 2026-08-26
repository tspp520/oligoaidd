"""LDAP 域账号认证 + JWT + 登录锁定（复用 complexa 方案）。"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
from ldap3.core.exceptions import LDAPException
from jose import jwt, JWTError

from app.config import settings
from app.database import execute_one, execute_insert

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7
LOCKOUT_MAX = 3
LOCKOUT_SECS = 300


async def _check_lockout(username: str):
    row = await execute_one(
        "SELECT fail_count, locked_until FROM login_lockouts WHERE username = $1",
        (username,),
    )
    if not row:
        return False, 0, 0
    locked_until = row["locked_until"]
    if locked_until is not None:
        now = datetime.now(timezone.utc)
        if now < locked_until:
            return True, int((locked_until - now).total_seconds()), row["fail_count"]
    return False, 0, row["fail_count"]


async def _record_failure(username: str):
    now = datetime.now(timezone.utc)
    row = await execute_one(
        "SELECT fail_count, locked_until FROM login_lockouts WHERE username = $1",
        (username,),
    )
    if row:
        count = row["fail_count"]
        locked_until = row["locked_until"]
        if locked_until is not None and now >= locked_until:
            count = 0
        count += 1
        new_locked = now + timedelta(seconds=LOCKOUT_SECS) if count >= LOCKOUT_MAX else None
        await execute_insert(
            """UPDATE login_lockouts SET fail_count=$1, locked_until=$2, last_attempt_at=$3
               WHERE username=$4""",
            (count, new_locked, now, username),
        )
    else:
        count = 1
        new_locked = now + timedelta(seconds=LOCKOUT_SECS) if count >= LOCKOUT_MAX else None
        await execute_insert(
            """INSERT INTO login_lockouts (username, fail_count, locked_until, last_attempt_at)
               VALUES ($1, $2, $3, $4)""",
            (username, count, new_locked, now),
        )
    if count >= LOCKOUT_MAX:
        return True, LOCKOUT_SECS, 0
    return False, 0, LOCKOUT_MAX - count


async def _record_success(username: str):
    await execute_insert("DELETE FROM login_lockouts WHERE username = $1", (username,))


async def _upsert_user(username: str, display: str, dept: str, email: str):
    now = datetime.now(timezone.utc)
    await execute_insert(
        """INSERT INTO users (username, display_name, department, email, auth_source, last_login_at, login_count)
           VALUES ($1,$2,$3,$4,'ldap',$5,1)
           ON CONFLICT (username) DO UPDATE SET
               display_name=EXCLUDED.display_name, department=EXCLUDED.department,
               email=EXCLUDED.email, last_login_at=EXCLUDED.last_login_at,
               login_count=users.login_count + 1""",
        (username, display, dept, email, now),
    )


class LDAPAuthenticator:
    def __init__(self):
        self.server_url = f"ldap://{settings.LDAP_HOST}:{settings.LDAP_PORT}"
        self.base_dn = settings.LDAP_BASE_DN
        self.domains = settings.ldap_domain_list or ["CP.shangpharma.com"]

    async def authenticate(self, username: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        if not username or not password:
            return False, "AUTH_MISSING_CREDENTIALS", None
        ukey = username.strip().lower()

        is_locked, remaining, _ = await _check_lockout(ukey)
        if is_locked:
            return False, "USER_LOCKED", {
                "attempts_left": 0, "locked_until": time.time() + remaining,
            }

        last_error = ""
        for domain in self.domains:
            success, error, user_info = self._try_bind(username, password, domain)
            if success:
                await _record_success(ukey)
                if user_info:
                    await _upsert_user(
                        user_info["username"], user_info["display_name"],
                        user_info["department"], user_info["email"],
                    )
                return True, "", user_info
            last_error = error
            if "invalidCredentials" in error or "Invalid credentials" in error.lower():
                break

        is_now_locked, lock_remaining, attempts_left = await _record_failure(ukey)
        meta = {"attempts_left": attempts_left}
        if is_now_locked:
            msg = "USER_LOCKED"
            meta["locked_until"] = time.time() + lock_remaining
        elif attempts_left == 1:
            msg = "WRONG_PASSWORD_LAST_ATTEMPT"
        else:
            msg = "WRONG_PASSWORD"
        logger.warning(
            "LDAP auth failed for %s (locked=%s att_left=%s err=%s)",
            username, is_now_locked, attempts_left, last_error,
        )
        return False, msg, meta

    def _try_bind(self, username: str, password: str, domain: str) -> Tuple[bool, str, Optional[dict]]:
        user_dn = f"{username}@{domain}"
        try:
            server = Server(self.server_url, use_ssl=False, get_info=ALL)
            conn = Connection(
                server, user=user_dn, password=password,
                authentication=SIMPLE, auto_bind=True,
            )
            user_info = self._get_user_info(conn, username, domain)
            conn.unbind()
            return True, "", user_info
        except LDAPException as e:
            return False, str(e), None
        except Exception:
            return False, "AUTH_SERVICE_ERROR", None

    def _get_user_info(self, conn, username: str, domain: str) -> dict:
        info = {
            "username": username,
            "display_name": username,
            "department": "",
            "email": f"{username}@{domain}",
        }
        try:
            conn.search(
                search_base=self.base_dn,
                search_filter=f"(sAMAccountName={username})",
                search_scope=SUBTREE,
                attributes=["cn", "mail", "displayName", "sAMAccountName", "department"],
            )
            if conn.entries:
                e = conn.entries[0]
                if getattr(e, "displayName", None):
                    info["display_name"] = str(e.displayName)
                if getattr(e, "mail", None):
                    info["email"] = str(e.mail)
                if getattr(e, "department", None):
                    info["department"] = str(e.department)
        except Exception:
            pass
        return info


def create_token(user_info: dict) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {
        "sub": user_info["username"],
        "display_name": user_info.get("display_name", ""),
        "department": user_info.get("department", ""),
        "email": user_info.get("email", ""),
        "exp": expire.timestamp(),
        "iat": now.timestamp(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


ldap_authenticator = LDAPAuthenticator()
