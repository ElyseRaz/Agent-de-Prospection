from enum import Enum as PyEnum


def enum_values(enum_cls: type[PyEnum]) -> list[str]:
    """A passer en `values_callable` de sa.Enum(...).

    Par defaut, SQLAlchemy persiste le `.name` (ex: "ADMIN") d'un Python Enum,
    pas son `.value` (ex: "admin"). Pour un StrEnum defini avec des membres en
    MAJUSCULES et des valeurs en minuscules (convention de ce projet), cela
    provoque une erreur Postgres "invalid input value for enum" des la
    premiere ecriture. `values_callable=enum_values` force l'usage de
    `.value`, coherent avec les labels crees par les migrations Alembic.
    """
    return [member.value for member in enum_cls]
