from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from ..models import Product, Category
from ..deps import get_current_active_superuser
from ..core.s3 import upload_file_to_local, save_base64_image
import json
from fastapi import Path, Body
from datetime import datetime, timezone

router = APIRouter()

PRODUCT_NOT_FOUND_MSG = "Product not found"


@router.get("/", response_model=List[dict])
async def read_products(
    skip: int = 0, limit: int = 100, search: Optional[str] = None
) -> Any:
    if search:
        docs = await Product.find_many({}).to_list()
        docs = [
            d for d in docs if search.lower() in (d.name or "").lower() and d.isActive
        ]
        docs = docs[skip : skip + limit]
    else:
        docs = (
            await Product.find_many({"isActive": True})
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    result = []
    for p in docs:
        stock = p.stockBySize or {}
        if isinstance(stock, str):
            try:
                stock = json.loads(stock)
            except Exception:
                stock = {}
        if isinstance(stock, dict):
            stock_list = [
                {"size": k.lstrip("s").replace("_", "."), "stock": v}
                for k, v in stock.items()
            ]
        else:
            stock_list = []
        result.append(
            {
                "id": str(p.id),
                "name": p.name,
                "price": p.price,
                "sizes": p.sizes,
                "stockBySize": stock_list,
                "images": p.images,
                "isActive": p.isActive,
                "isFeatured": p.isFeatured,
            }
        )
    return result


@router.post("/", response_model=dict)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    sizes: str = Form(...),
    colors: str = Form(...),
    category_ids: str = Form(...),
    images_base64: Optional[str] = Form(None),
    images_files: Optional[List[UploadFile]] = File(None),
    _=Depends(get_current_active_superuser),
):
    sizes_data = json.loads(sizes)
    colors_list = json.loads(colors)
    category_ids = json.loads(category_ids)

    stock_by_size_dict = {f"s{str(size).replace('.', '_')}": 0 for size in sizes_data}

    image_urls = []
    if images_base64:
        arr = images_base64.split(";") if ";" in images_base64 else [images_base64]
        for i, b64 in enumerate(arr):
            fname = f"{name.replace(' ', '_')}_{i}.jpg"
            url = save_base64_image(b64, fname, folder="products")
            image_urls.append(url)
    if images_files:
        for f in images_files:
            url = await upload_file_to_local(f, folder="products")
            image_urls.append(url)

    p = Product(
        name=name,
        description=description,
        price=price,
        sizes=sizes_data,
        colors=colors_list,
        images=image_urls,
        stockBySize=stock_by_size_dict,
        isActive=True,
        isFeatured=False,
    )
    await p.insert()

    # Attach categories as simple list of ids for now
    if category_ids:
        p.categories = [{"categoryId": cid} for cid in category_ids]
        await p.save()

    return {"id": str(p.id), "name": p.name, "images": p.images}


@router.get("/{product_id}", response_model=dict)
async def get_product(product_id: str = Path(...)) -> dict:
    p = await Product.get(product_id)
    if not p or not p.isActive:
        raise HTTPException(status_code=404, detail=PRODUCT_NOT_FOUND_MSG)

    stock = p.stockBySize or {}
    if isinstance(stock, str):
        try:
            stock = json.loads(stock)
        except Exception:
            stock = {}
    stock_list = []
    if isinstance(stock, dict):
        stock_list = [
            {"size": k.lstrip("s").replace("_", "."), "stock": v}
            for k, v in stock.items()
        ]

    return {
        "id": str(p.id),
        "name": p.name,
        "price": p.price,
        "sizes": p.sizes,
        "stockBySize": stock_list,
        "images": p.images,
        "isActive": p.isActive,
        "isFeatured": p.isFeatured,
    }


@router.put("/{product_id}", response_model=dict)
async def update_product(
    product_id: str = Path(...),
    product_in: dict = Body(...),
    _=Depends(get_current_active_superuser),
):
    p = await Product.get(product_id)
    if not p:
        raise HTTPException(status_code=404, detail=PRODUCT_NOT_FOUND_MSG)
    # update allowed fields
    for fld in (
        "name",
        "description",
        "price",
        "sizes",
        "colors",
        "isActive",
        "isFeatured",
    ):
        if fld in product_in:
            setattr(p, fld, product_in.get(fld))
    if "stockBySize" in product_in:
        p.stockBySize = product_in.get("stockBySize")
    if "images" in product_in:
        p.images = product_in.get("images")
    p.updatedAt = datetime.now(tz=timezone.utc)
    await p.save()
    return {"id": str(p.id), "name": p.name, "images": p.images}


@router.delete("/{product_id}")
async def delete_product(
    product_id: str = Path(...), _=Depends(get_current_active_superuser)
):
    p = await Product.get(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    await p.delete()
    return {"ok": True}
