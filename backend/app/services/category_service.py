"""Category business logic."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Category
from app.repositories.category import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.common import Page
from app.schemas.inventory import CategoryBrief
from app.services.exceptions import DuplicateError, NotFoundError, ReferencedError


class CategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CategoryRepository(db)

    def list_categories(self, *, search: str | None, page: int, page_size: int) -> Page[Category]:
        rows, total = self.repo.list(search=search, offset=(page - 1) * page_size, limit=page_size)
        items = [row[0] for row in rows]
        return Page.build(items=items, total=total, page=page, page_size=page_size)

    def get_category(self, category_id: int) -> Category:
        category = self.repo.get(category_id)
        if category is None:
            raise NotFoundError(f"Category {category_id} not found.")
        return category

    def create_category(self, data: CategoryCreate) -> Category:
        name = data.name.strip()
        if self.repo.get_by_name(name):
            raise DuplicateError(f"Category '{name}' already exists.")
        return self.repo.add(Category(name=name, description=data.description))

    def update_category(self, category_id: int, data: CategoryUpdate) -> Category:
        category = self.get_category(category_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            name = changes["name"].strip()
            existing = self.repo.get_by_name(name)
            if existing and existing.id != category.id:
                raise DuplicateError(f"Category '{name}' already exists.")
            category.name = name
        if "description" in changes:
            category.description = changes["description"]
        self.db.flush()
        return category

    def delete_category(self, category_id: int) -> None:
        category = self.get_category(category_id)
        used_by = self.repo.count_products(category.id)
        if used_by:
            raise ReferencedError(
                f"Category '{category.name}' is used by {used_by} product(s) and cannot be deleted."
            )
        self.repo.delete(category)

    def product_count(self, category_id: int) -> int:
        return self.repo.count_products(category_id)


def category_brief(category: Category) -> CategoryBrief:
    return CategoryBrief(id=category.id, name=category.name)
