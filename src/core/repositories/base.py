"""
Base repository with common functionality.
"""

from typing import Optional
from sqlmodel import Session

from ..database import get_session


class BaseRepository:
    """Base repository with common functionality"""

    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def get_session(self) -> Session:
        """Get database session"""
        if self._session:
            return self._session
        return get_session()
