import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer,
                primary_key=True,
                autoincrement=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    def before_save(self, *args, **kwargs):
        pass

    def after_save(self, *args, **kwargs):
        pass

    def save(self, session, commit=True, *args, **kwargs):
        self.before_save(*args, **kwargs)
        self.created_at = kwargs.get('timestamp', datetime.datetime.now())
        session.add(self)
        if commit:
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                raise e

        self.after_save(*args, **kwargs)

    def before_merge(self, *args, **kwargs):
        pass

    def after_merge(self, *args, **kwargs):
        pass

    def merge(self, session, commit=True, *args, **kwargs):
        self.before_save(*args, **kwargs)
        if self.created_at is None:
            self.created_at = kwargs.get('timestamp', datetime.datetime.now())
        else:
            self.updated_at = kwargs.get('timestamp', datetime.datetime.now())
        session.merge(self)
        if commit:
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                raise e

        self.after_save(*args, **kwargs)

    def before_update(self, *args, **kwargs):
        pass

    def after_update(self, *args, **kwargs):
        pass

    def update(self, session, *args, **kwargs):
        self.before_update(*args, **kwargs)
        self.updated_at = kwargs.get('timestamp', datetime.datetime.now())
        session.commit()
        self.after_update(*args, **kwargs)

    def delete(self, session, commit=True):
        session.delete(self)
        if commit:
            session.commit()


class Resource(BaseModel):
    __tablename__ = "resource"
    id = Column(String, primary_key=True)
    title = Column(String)
    tag_links = relationship("TagLink", back_populates="resource", cascade="all,delete-orphan")
    author_links = relationship("AuthorLink", back_populates="resource", cascade="all,delete-orphan")


class Tag(BaseModel):
    __tablename__ = "tag"
    updated_at = None
    tag = Column(String, unique=True, nullable=False)
    display = Column(String)
    tag_links = relationship("TagLink", back_populates="tag", cascade="all,delete-orphan")


class TagLink(BaseModel):
    __tablename__ = "tag_link"
    id = None
    updated_at = None
    resource_id = Column(String,
                         ForeignKey('resource.id'),
                         primary_key=True)
    tag_id = Column(Integer,
                    ForeignKey('tag.id'),
                    primary_key=True)
    resource = relationship(Resource, back_populates="tag_links")
    tag = relationship(Tag, back_populates="tag_links")


class Author(BaseModel):
    __tablename__ = "author"
    name = Column(String, unique=True, nullable=False)
    author_links = relationship("AuthorLink", back_populates="author", cascade="all,delete-orphan")


class AuthorLink(BaseModel):
    __tablename__ = "author_link"
    id = None
    updated_at = None
    resource_id = Column(String,
                         ForeignKey('resource.id'),
                         primary_key=True)
    author_id = Column(Integer,
                       ForeignKey('author.id'),
                       primary_key=True)
    resource = relationship(Resource, back_populates="author_links")
    author = relationship(Author, back_populates="author_links")
