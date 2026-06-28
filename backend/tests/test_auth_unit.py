import pytest
from fastapi import HTTPException

from auth import decode_token, get_current_lawyer, hash_password, verify_password


class TestVerifyPassword:
    def test_verify_password_correct(self):
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong", hashed) is False

    def test_verify_password_empty(self):
        hashed = hash_password("password")
        assert verify_password("", hashed) is False


class TestDecodeToken:
    def test_decode_token_malformed(self):
        with pytest.raises(HTTPException) as exc:
            decode_token("this.is.not.a.jwt")
        assert exc.value.status_code == 401
        assert "Invalid or expired token" in exc.value.detail

    def test_decode_token_empty(self):
        with pytest.raises(HTTPException) as exc:
            decode_token("")
        assert exc.value.status_code == 401

    def test_decode_token_nonsense(self):
        with pytest.raises(HTTPException) as exc:
            decode_token("eyJ.eyJ.eyJ")
        assert exc.value.status_code == 401


class TestGetCurrentLawyer:
    @pytest.mark.asyncio
    async def test_missing_credentials(self):
        with pytest.raises(HTTPException) as exc:
            await get_current_lawyer(None)
        assert exc.value.status_code == 401
        assert "Missing authorization header" in exc.value.detail
