'use client';

import React from 'react';
import { SizeStock, EuroSizeStock, UpdateEuroSizesFunction } from '@/types/product';

interface ProductFormProps {
  formData: {
    name: string;
    description: string;
    price: number;
    sizes: SizeStock[];
    colors: string[];
    images: string[];
    isActive: boolean;
    isFeatured: boolean;
  };
  updateField: (field: string, value: any) => void;
  updateSizes: UpdateEuroSizesFunction;
  addImages: (images: string[]) => void;
  removeImage: (index: number) => void;
  updateColors: (colors: string[]) => void;
}

export default function ProductForm({
  formData,
  updateField,
  updateSizes,
  addImages,
  removeImage,
  updateColors,
}: ProductFormProps) {
  // Convert SizeStock to EuroSizeStock format for the updateSizes function
  const handleSizeUpdate = (sizes: SizeStock[]) => {
    // Transform SizeStock[] to EuroSizeStock[]
    const euroSizes: EuroSizeStock[] = sizes.map((size) => ({
      euro_size: size.size,
      stock: size.stock
    }));
    updateSizes(euroSizes);
  };

  return (
    <div className="product-form">
      <h2>Add New Product</h2>
      
      <div className="form-field">
        <label htmlFor="name">Product Name:</label>
        <input
          id="name"
          type="text"
          value={formData.name}
          onChange={(e) => updateField('name', e.target.value)}
        />
      </div>

      <div className="form-field">
        <label htmlFor="description">Description:</label>
        <textarea
          id="description"
          value={formData.description}
          onChange={(e) => updateField('description', e.target.value)}
        />
      </div>

      <div className="form-field">
        <label htmlFor="price">Price:</label>
        <input
          id="price"
          type="number"
          value={formData.price}
          onChange={(e) => updateField('price', parseFloat(e.target.value))}
        />
      </div>

      <div className="form-field">
        <h3>Sizes and Stock</h3>
        {formData.sizes.map((size, index) => (
          <div key={index} className="size-stock-row">
            <input
              type="text"
              placeholder="Size"
              value={size.size}
              onChange={(e) => {
                const newSizes = [...formData.sizes];
                newSizes[index] = { ...size, size: e.target.value };
                handleSizeUpdate(newSizes);
              }}
            />
            <input
              type="number"
              placeholder="Stock"
              value={size.stock}
              onChange={(e) => {
                const newSizes = [...formData.sizes];
                newSizes[index] = { ...size, stock: parseInt(e.target.value) || 0 };
                handleSizeUpdate(newSizes);
              }}
            />
          </div>
        ))}
        <button 
          type="button"
          onClick={() => {
            const newSizes = [...formData.sizes, { size: '', stock: 0 }];
            handleSizeUpdate(newSizes);
          }}
        >
          Add Size
        </button>
      </div>

      <div className="form-field">
        <h3>Colors</h3>
        {formData.colors.map((color, index) => (
          <div key={index} className="color-row">
            <input
              type="text"
              value={color}
              onChange={(e) => {
                const newColors = [...formData.colors];
                newColors[index] = e.target.value;
                updateColors(newColors);
              }}
            />
          </div>
        ))}
        <button 
          type="button"
          onClick={() => updateColors([...formData.colors, ''])}
        >
          Add Color
        </button>
      </div>

      <div className="form-field">
        <h3>Images</h3>
        {formData.images.map((image, index) => (
          <div key={index} className="image-row">
            <img src={image} alt={`Product ${index}`} style={{ width: '100px', height: '100px' }} />
            <button type="button" onClick={() => removeImage(index)}>Remove</button>
          </div>
        ))}
        <button 
          type="button"
          onClick={() => addImages(['https://example.com/placeholder.jpg'])}
        >
          Add Image
        </button>
      </div>

      <div className="form-field">
        <label>
          <input
            type="checkbox"
            checked={formData.isActive}
            onChange={(e) => updateField('isActive', e.target.checked)}
          />
          Active
        </label>
      </div>

      <div className="form-field">
        <label>
          <input
            type="checkbox"
            checked={formData.isFeatured}
            onChange={(e) => updateField('isFeatured', e.target.checked)}
          />
          Featured
        </label>
      </div>
    </div>
  );
}