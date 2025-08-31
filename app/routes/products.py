from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from ..models import Product, Category, Subcategory
from ..deps import get_current_active_superuser
from ..core.s3 import upload_file_to_local, save_base64_image
import json
from fastapi import Path, Body
from datetime import datetime, timezone
from fastapi import Request
import os
import logging

logger = logging.getLogger(__name__)

GCS_PREFIX = "gcs://"


# Helper: convert stored gcs:// URIs to public S3 URLs for frontend
def resolve_public_image_url(uri: Optional[str]):
    if not uri:
        return uri
    try:
        u = str(uri)
    except Exception:
        return uri
    if not u.startswith(GCS_PREFIX):
        return u
    # remove prefix
    key = u.replace(GCS_PREFIX, "")
    public_url = os.getenv("S3_PUBLIC_URL")
    if public_url:
        return f"{public_url.rstrip('/')}/{key}"
    bucket = os.getenv("S3_BUCKET")
    if bucket:
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    # fallback: return the key path so frontend can try relative proxy
    return f"/{key}"


def _parse_presign_payload(d: dict):
    try:
        name = d.get("name")
        description = d.get("description")
        price_raw = d.get("price")
        price = float(price_raw) if price_raw not in (None, "") else 0.0
        sizes = d.get("sizes") or []
        colors = d.get("colors") or []
        category_ids = d.get("categoryIds") or []
        images_in = d.get("images") or []
        return name, description, price, sizes, colors, category_ids, images_in
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Invalid input for presign-create: %s", exc)
        raise HTTPException(status_code=400, detail=f"Invalid input: {exc}")


def _normalize_sizes(sizes_input):
    if not sizes_input:
        return []
    # If it's already a list of simple values, stringify them
    if isinstance(sizes_input, list):
        out = []
        for s in sizes_input:
            if isinstance(s, dict):
                # accept keys 'size' or 'value'
                val = s.get("size") if ("size" in s) else s.get("value")
                out.append(str(val))
            else:
                out.append(str(s))
        return out
    # If it's a comma-separated string
    if isinstance(sizes_input, str):
        return [x.strip() for x in sizes_input.split(",") if x.strip()]
    # fallback
    return []


def _normalize_images(images_in):
    image_urls = []
    for img in images_in:
        if (
            isinstance(img, str)
            and not img.startswith("/")
            and not img.startswith("http")
            and not img.startswith(GCS_PREFIX)
        ):
            image_urls.append(f"gcs://{img}")
        else:
            image_urls.append(img)
    return image_urls


def _parse_json_field(value: Optional[str], default=None):
    if default is None:
        default = []
    if value is None:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _to_stock_key(value):
    return f"s{str(value).replace('.', '_')}"


def _safe_int(value):
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return 0


def _parse_stock_list_simple(parsed_list):
    """
    Parse list-like stock representations:
      - list of dicts: [{"size": "...", "stock": N}, ...]
      - list of pairs: [["M", 3], ...] or tuples
    Returns dict of normalized keys -> int stock.
    """
    result = {}
    for entry in parsed_list:
        if isinstance(entry, dict):
            sz = entry.get("size")
            st = entry.get("stock", 0)
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            sz, st = entry[0], entry[1]
        else:
            continue
        if sz is None:
            continue
        result[_to_stock_key(sz)] = _safe_int(st)
    return result


def _parse_stock_dict_simple(parsed_dict):
    """
    Parse dict-like stock representations:
      - keys may already be "s<size>" or raw sizes
    """
    result = {}
    for k, v in parsed_dict.items():
        key = k if isinstance(k, str) and k.startswith("s") else _to_stock_key(k)
        result[key] = _safe_int(v)
    return result


def _parse_stock_by_size_field(stock_by_size_raw: Optional[str], sizes_fallback=None):
    # Accept JSON string of list/dict or None. Return normalized dict mapping 's<size>'->int
    sizes_fallback = sizes_fallback or []
    if not stock_by_size_raw:
        return {}
    try:
        parsed = json.loads(stock_by_size_raw)
    except Exception:
        return {}

    if isinstance(parsed, list):
        out = _parse_stock_list_simple(parsed)
    elif isinstance(parsed, dict):
        out = _parse_stock_dict_simple(parsed)
    else:
        out = {}

    if not out and sizes_fallback:
        out = _build_stock_by_size_dict(sizes_fallback)

    return out


async def _process_product_images(
    name, images_base64: Optional[str], images_files: Optional[List[UploadFile]]
):
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
    return image_urls


def _build_stock_by_size_dict(sizes_norm):
    return {f"s{str(size).replace('.', '_')}": 0 for size in sizes_norm}


async def _create_product_from_parsed(
    name,
    description,
    price,
    sizes,
    colors,
    image_urls,
    category_ids,
    stock_by_size_dict,
):
    p = Product(
        name=name,
        description=description,
        price=price,
        sizes=sizes,
        colors=colors,
        images=image_urls,
        stockBySize=stock_by_size_dict,
        isActive=True,
        isFeatured=False,
    )
    await p.insert()

    if category_ids:
        # ensure iterable
        try:
            p.categories = [{"categoryId": cid} for cid in category_ids]
        except Exception:
            # Maybe single value, coerce
            p.categories = [{"categoryId": category_ids}]
        await p.save()

    return {
        "id": str(p.id),
        "name": p.name,
        "images": [resolve_public_image_url(i) for i in (p.images or [])],
    }


router = APIRouter()

PRODUCT_NOT_FOUND_MSG = "Product not found"


def _normalize_product_stock(stock_raw) -> List[dict]:
    """
    Normalize possible stored stock representations into a list of
    {"size": "...", "stock": N} entries.
    Accepts JSON string, dict, list-of-dicts, or list-of-pairs.
    Delegates parsing to the existing simple parsers.
    """
    if not stock_raw:
        return []

    # If stored as JSON string, try to parse it
    parsed = stock_raw
    if isinstance(stock_raw, str):
        try:
            parsed = json.loads(stock_raw)
        except Exception:
            return []

    stock_dict = {}
    if isinstance(parsed, dict):
        stock_dict = _parse_stock_dict_simple(parsed)
    elif isinstance(parsed, list):
        stock_dict = _parse_stock_list_simple(parsed)
    else:
        return []

    return [
        {"size": k.lstrip("s").replace("_", "."), "stock": v}
        for k, v in stock_dict.items()
    ]


async def _resolve_product_categories(p) -> List[dict]:
    """
    Given a Product document `p`, resolve its stored category references
    (stored as [{'categoryId': id}, ...]) into a list of {id, name} objects
    suitable for the frontend. This keeps responses stable even for legacy
    documents that might only store ids.
    """
    out = []
    if not getattr(p, "categories", None):
        return out
    for entry in p.categories:
        try:
            cid = None
            if isinstance(entry, dict):
                cid = entry.get("categoryId") or entry.get("id")
            else:
                cid = entry
            if not cid:
                continue
            # Try to fetch Category document to obtain name
            try:
                cat = await Category.get(cid)
            except Exception:
                cat = None
            if cat:
                out.append({"id": str(cat.id), "name": cat.name})
            else:
                out.append({"id": str(cid), "name": None})
        except Exception:
            continue
    return out


async def _resolve_product_subcategory(p) -> Optional[dict]:
    """
    Resolve a product's `subcategoryId` into {id, name} or return None.
    """
    cid = getattr(p, "subcategoryId", None)
    if not cid:
        return None
    try:
        sub = await Subcategory.get(cid)
    except Exception:
        sub = None
    if sub:
        return {"id": str(sub.id), "name": sub.name}
    return {"id": str(cid), "name": None}


@router.get("/", response_model=List[dict])
async def read_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    request: Request = None,
) -> Any:
    # Defensive: if DB not initialized on startup, return 503 so callers know it's a server-side issue.
    try:
        if request is not None and not getattr(request.app.state, "db_connected", True):
            logger.warning("Attempt to access products while DB not connected")
            raise HTTPException(
                status_code=503, detail="Service temporarily unavailable"
            )

        # Fetch documents; errors here indicate DB connectivity or query issues.
        try:
            if search:
                docs = await Product.find_many({}).to_list()
                docs = [
                    d
                    for d in docs
                    if search.lower() in (d.name or "").lower() and d.isActive
                ]
                docs = docs[skip : skip + limit]
            else:
                docs = (
                    await Product.find_many({"isActive": True})
                    .skip(skip)
                    .limit(limit)
                    .to_list()
                )
        except Exception as db_exc:
            logger.exception("Database error while fetching products: %s", db_exc)
            # Surface a 500 to the caller with minimal details
            raise HTTPException(status_code=500, detail="Internal Server Error")

        result = []
        for p in docs:
            try:
                stock_list = _normalize_product_stock(p.stockBySize or {})
                result.append(
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "price": p.price,
                        "sizes": p.sizes,
                        "stockBySize": stock_list,
                        "categories": await _resolve_product_categories(p),
                        "subcategory": await _resolve_product_subcategory(p),
                        "images": [
                            resolve_public_image_url(i) for i in (p.images or [])
                        ],
                        "isActive": p.isActive,
                        "isFeatured": p.isFeatured,
                    }
                )
            except Exception as item_exc:
                # Skip individual bad documents but keep serving the rest
                logger.exception(
                    "Skipping product during serialization (id=%s): %s",
                    getattr(p, "id", None),
                    item_exc,
                )
                continue
        return result
    except HTTPException:
        # Re-raise HTTPExceptions so FastAPI handles them unchanged
        raise
    except Exception as exc:
        logger.exception("Unhandled error in read_products: %s", exc)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/featured", response_model=List[dict])
async def read_featured_products(skip: int = 0, limit: int = 100) -> Any:
    """Return featured products with the same transformation as the main listing.
    Defensive: never raise unhandled exceptions; convert unexpected representations
    into safe defaults so frontend receives a stable JSON array.
    """
    try:
        # Defensive: if the app hasn't initialized the DB, return empty list or surface 503
        # We can't import 'app' directly here due to circular imports; rely on request.app at runtime
        # Fallback: check Product.get_settings indirectly by catching the specific exception
        try:
            docs = (
                await Product.find_many({"isActive": True, "isFeatured": True})
                .skip(skip)
                .limit(limit)
                .to_list()
            )
        except Exception as db_exc:
            # This will capture CollectionWasNotInitialized and other DB errors
            logger.exception(
                "Database error while fetching featured products: %s", db_exc
            )
            raise HTTPException(
                status_code=503, detail="Service temporarily unavailable"
            )

        result = []
        for p in docs:
            try:
                stock_list = _normalize_product_stock(p.stockBySize or {})
                result.append(
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "price": p.price,
                        "sizes": p.sizes,
                        "stockBySize": stock_list,
                        "categories": await _resolve_product_categories(p),
                        "subcategory": await _resolve_product_subcategory(p),
                        "images": [
                            resolve_public_image_url(i) for i in (p.images or [])
                        ],
                        "isActive": p.isActive,
                        "isFeatured": p.isFeatured,
                    }
                )
            except Exception:
                # Skip single bad document but keep processing others
                logger.exception(
                    "Error serializing featured product: %s", getattr(p, "id", None)
                )
                continue
        return result
    except HTTPException:
        # Let FastAPI handle HTTPExceptions (like the 503 we raise above)
        raise
    except Exception as exc:
        logger.exception("Error fetching featured products: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=dict)
async def create_product(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    sizes: str = Form(...),
    colors: str = Form(...),
    category_ids: str = Form(...),
    stock_by_size: Optional[str] = Form(None, alias="stockBySize"),
    images_base64: Optional[str] = Form(None),
    images_files: Optional[List[UploadFile]] = File(None),
    _=Depends(get_current_active_superuser),
):
    sizes_data = _parse_json_field(sizes, [])
    colors_list = _parse_json_field(colors, [])
    category_ids_list = _parse_json_field(category_ids, [])
    stock_by_size_dict = _parse_stock_by_size_field(stock_by_size, sizes_data)
    image_urls = await _process_product_images(name, images_base64, images_files)
    product = await _create_product_object(
        name,
        description,
        price,
        sizes_data,
        colors_list,
        image_urls,
        stock_by_size_dict,
        category_ids_list,
    )
    return product


def _parse_json_field(field, fallback=None):
    try:
        return json.loads(field)
    except Exception:
        return fallback if fallback is not None else []


def _parse_stock_by_size_field(stock_by_size, sizes_data):
    if not stock_by_size:
        return {f"s{str(size).replace('.', '_')}": 0 for size in sizes_data}
    try:
        parsed = json.loads(stock_by_size)
        if isinstance(parsed, list):
            return _stock_dict_from_list(parsed)
        elif isinstance(parsed, dict):
            return _stock_dict_from_dict(parsed)
    except Exception:
        pass
    return {f"s{str(size).replace('.', '_')}": 0 for size in sizes_data}


def _stock_dict_from_list(parsed_list):
    stock_dict = {}
    for entry in parsed_list:
        try:
            sz = str(entry.get("size") if isinstance(entry, dict) else entry[0])
            st = int(entry.get("stock") if isinstance(entry, dict) else entry[1])
            key = f"s{sz.replace('.', '_')}"
            stock_dict[key] = st
        except Exception:
            continue
    return stock_dict


def _stock_dict_from_dict(parsed_dict):
    stock_dict = {}
    for k, v in parsed_dict.items():
        key = f"s{str(k).replace('.', '_')}"
        try:
            stock_dict[key] = int(v)
        except Exception:
            stock_dict[key] = 0
    return stock_dict


async def _process_product_images(name, images_base64, images_files):
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
    return image_urls


async def _create_product_object(
    name,
    description,
    price,
    sizes_data,
    colors_list,
    image_urls,
    stock_by_size_dict,
    category_ids_list,
):
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
    if category_ids_list:
        p.categories = [{"categoryId": cid} for cid in category_ids_list]
        await p.save()
    return {
        "id": str(p.id),
        "name": p.name,
        "images": [resolve_public_image_url(i) for i in (p.images or [])],
    }


def _to_size_key(sz):
    return f"s{str(sz).replace('.', '_')}"


def _to_int_value(v):
    try:
        return int(float(v))
    except Exception:
        return 0


def _parse_sizes_list(sizes_list):
    if not isinstance(sizes_list, list):
        return None
    stock = {}
    for entry in sizes_list:
        if not isinstance(entry, dict):
            continue
        sz = entry.get("size")
        if sz is None:
            continue
        st = entry.get("stock", 0)
        stock[_to_size_key(sz)] = _to_int_value(st)
    return stock or None


def _parse_provided_list(prov_list):
    if not isinstance(prov_list, list):
        return None
    stock = {}
    for entry in prov_list:
        if isinstance(entry, dict):
            sz = entry.get("size")
            st = entry.get("stock", 0)
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            sz, st = entry[0], entry[1]
        else:
            continue
        if sz is None:
            continue
        stock[_to_size_key(sz)] = _to_int_value(st)
    return stock or None


def _parse_provided_dict(prov_dict):
    if not isinstance(prov_dict, dict):
        return None
    stock = {}
    for k, v in prov_dict.items():
        key = k if isinstance(k, str) and k.startswith("s") else _to_size_key(k)
        stock[key] = _to_int_value(v)
    return stock or None


def _extract_stock_by_size(data, sizes, sizes_norm):
    """
    Extracts stock by size from various input formats using small helpers for
    clarity and minimal branching.
    """
    provided = data.get("stockBySize")

    # Priority 1: nothing provided -> try to infer from sizes list entries
    if provided is None:
        inferred = _parse_sizes_list(sizes)
        if inferred is not None:
            return inferred
        return _build_stock_by_size_dict(sizes_norm)

    # Priority 2: explicit provided value handling
    if isinstance(provided, list):
        parsed = _parse_provided_list(provided)
        if parsed is not None:
            return parsed

    if isinstance(provided, dict):
        parsed = _parse_provided_dict(provided)
        if parsed is not None:
            return parsed

    # Final fallback: default zeroed stock for normalized sizes
    return _build_stock_by_size_dict(sizes_norm)


async def _handle_presign_create(data):
    logger.debug("presign-create incoming payload keys: %s", list(data.keys()))
    name, description, price, sizes, colors, category_ids, images_in = (
        _parse_presign_payload(data)
    )
    sizes_norm = _normalize_sizes(sizes)
    logger.debug("presign-create normalized sizes: %s", sizes_norm)
    logger.info(
        "presign-create request: name=%s price=%s sizes=%d colors=%d images=%d categoryIds=%s",
        name,
        price,
        len(sizes_norm) if hasattr(sizes_norm, "__len__") else 0,
        len(colors) if hasattr(colors, "__len__") else 0,
        len(images_in) if hasattr(images_in, "__len__") else 0,
        category_ids,
    )
    image_urls = _normalize_images(images_in)
    logger.debug("presign-create normalized images: %s", image_urls)
    stock_by_size_dict = _extract_stock_by_size(data, sizes, sizes_norm)
    result = await _create_product_from_parsed(
        name,
        description,
        price,
        sizes_norm,
        colors,
        image_urls,
        category_ids,
        stock_by_size_dict,
    )
    logger.info("presign-create succeeded: product_id=%s", result.get("id"))
    return result


@router.post("/presign-create", response_model=dict)
async def create_product_presigned(
    data: dict = Body(...), _=Depends(get_current_active_superuser)
):
    """
    Create product when images are already uploaded and provided as object keys.
    Expects JSON body with: name, description, price, sizes (array), colors (array), categoryIds (array), images (array of keys or URLs), macroCategoryId optional
    """
    try:
        return await _handle_presign_create(data)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error creating product (presign-create): %s", exc)
        raise HTTPException(
            status_code=500, detail="Internal server error: could not create product"
        )


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
        "categories": await _resolve_product_categories(p),
        "subcategory": await _resolve_product_subcategory(p),
        "images": [resolve_public_image_url(i) for i in (p.images or [])],
        "isActive": p.isActive,
        "isFeatured": p.isFeatured,
    }


def _normalize_sizes_for_update(product_in):
    sizes_with_stock = None
    if "sizes" in product_in and isinstance(product_in.get("sizes"), list):
        maybe = product_in.get("sizes")
        if any(isinstance(x, dict) for x in maybe):
            sizes_with_stock = maybe
            sizes_only = [
                str(x.get("size"))
                for x in maybe
                if isinstance(x, dict) and x.get("size") is not None
            ]
            product_in["sizes"] = sizes_only
    return sizes_with_stock


def _update_simple_fields(p, product_in):
    for fld in (
        "name",
        "description",
        "price",
        "sizes",
        "colors",
        "isActive",
        "isFeatured",
        "stock",
    ):
        if fld in product_in:
            setattr(p, fld, product_in.get(fld))


def _parse_stock_list(provided):
    stock_dict = {}
    for entry in provided:
        sz, st = None, 0
        if isinstance(entry, dict):
            sz = entry.get("size")
            st = entry.get("stock", 0)
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            sz, st = entry[0], entry[1]
        if sz is not None:
            key = f"s{str(sz).replace('.', '_')}"
            try:
                stock_dict[key] = int(st)
            except Exception:
                stock_dict[key] = 0
    return stock_dict


def _parse_stock_dict(provided):
    stock_dict = {}
    for k, v in provided.items():
        key = (
            k
            if isinstance(k, str) and k.startswith("s")
            else f"s{str(k).replace('.', '_')}"
        )
        try:
            stock_dict[key] = int(v)
        except Exception:
            stock_dict[key] = 0
    return stock_dict


def _fallback_stock(sizes):
    return {f"s{str(s).replace('.', '_')}": 0 for s in sizes}


def _normalize_stock_by_size(product_in, p, sizes_with_stock):
    provided = product_in.get("stockBySize")
    sizes_list = product_in.get("sizes") or p.sizes or []

    if isinstance(provided, list):
        stock_by_size_dict = _parse_stock_list(provided)
    elif isinstance(provided, dict):
        stock_by_size_dict = _parse_stock_dict(provided)
    else:
        stock_by_size_dict = {}

    if (
        not stock_by_size_dict
        and sizes_with_stock
        and isinstance(sizes_with_stock, list)
    ):
        stock_by_size_dict = _parse_stock_list(sizes_with_stock)

    if not stock_by_size_dict:
        stock_by_size_dict = _fallback_stock(sizes_list)

    return stock_by_size_dict


def _update_images(p, product_in):
    if "images" in product_in:
        p.images = product_in.get("images")


def _handle_save(p):
    p.updatedAt = datetime.now(tz=timezone.utc)
    try:
        return p.save()
    except Exception as exc:
        logger.exception("Error saving product on update: %s", exc)
        raise HTTPException(
            status_code=500, detail="Internal server error: could not save product"
        )


@router.put("/{product_id}", response_model=dict)
async def update_product(
    product_id: str = Path(...),
    product_in: dict = Body(...),
    _=Depends(get_current_active_superuser),
):
    p = await Product.get(product_id)
    if not p:
        raise HTTPException(status_code=404, detail=PRODUCT_NOT_FOUND_MSG)

    sizes_with_stock = _normalize_sizes_for_update(product_in)
    _update_simple_fields(p, product_in)
    _update_stock_by_size(p, product_in, sizes_with_stock)
    _update_images(p, product_in)
    _update_categories(p, product_in)
    _update_subcategory(p, product_in)

    p.updatedAt = datetime.now(tz=timezone.utc)
    await _save_product(p)
    return {
        "id": str(p.id),
        "name": p.name,
        "images": [resolve_public_image_url(i) for i in (p.images or [])],
    }


def _update_stock_by_size(p, product_in, sizes_with_stock):
    if "stockBySize" in product_in or sizes_with_stock:
        stock_by_size_dict = _normalize_stock_by_size(product_in, p, sizes_with_stock)
        p.stockBySize = stock_by_size_dict


def _update_categories(p, product_in):
    if "categoryIds" not in product_in:
        return
    incoming = product_in.get("categoryIds") or []
    incoming = _parse_category_ids(incoming)
    p.categories = [{"categoryId": cid} for cid in incoming if cid]


def _parse_category_ids(incoming):
    # Helper to parse categoryIds from various formats
    if isinstance(incoming, str):
        try:
            parsed = json.loads(incoming)
            if isinstance(parsed, list):
                return parsed
            return [parsed] if parsed else []
        except Exception:
            return [incoming] if incoming else []
    if isinstance(incoming, list):
        return incoming
    return [incoming] if incoming else []


def _update_subcategory(p, product_in):
    if "subcategoryId" in product_in:
        sub_in = product_in.get("subcategoryId")
        if isinstance(sub_in, str):
            try:
                maybe = json.loads(sub_in)
                sub_in = maybe
            except Exception:
                pass
        p.subcategoryId = sub_in or None


async def _save_product(p):
    try:
        await p.save()
    except Exception as exc:
        logger.exception("Error saving product on update: %s", exc)
        raise HTTPException(
            status_code=500, detail="Internal server error: could not save product"
        )


@router.delete("/{product_id}")
async def delete_product(
    product_id: str = Path(...), _=Depends(get_current_active_superuser)
):
    p = await Product.get(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    await p.delete()
    return {"ok": True}
