from app.config.database import engine
from app.models.base import Base
from app.models import entities  # noqa: F401

def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Schema analítico criado/validado com sucesso.")

if __name__ == "__main__":
    main()
