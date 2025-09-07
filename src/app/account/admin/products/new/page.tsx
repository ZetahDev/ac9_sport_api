'use client';

import React, { useState } from 'react';
import ProductForm from '@/components/ProductForm';
import { SizeStock, EuroSizeStock, ProductFormData } from '@/types/product';

export default function NewProductPage() {
  const [formData, setFormData] = useState<ProductFormData>({
    name: '',
    description: '',
    price: 0,
    sizes: [],
    colors: [],
    images: [],
    isActive: true,
    isFeatured: false,
  });

  const updateField = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // This function expects EuroSizeStock[] as parameter
  const updateSizes = (sizes: EuroSizeStock[]) => {
    // Convert EuroSizeStock back to SizeStock for internal state
    const sizeStocks: SizeStock[] = sizes.map((euroSize) => ({
      size: euroSize.euro_size,
      stock: euroSize.stock
    }));
    
    setFormData(prev => ({
      ...prev,
      sizes: sizeStocks
    }));
  };

  const addImages = (images: string[]) => {
    setFormData(prev => ({
      ...prev,
      images: [...prev.images, ...images]
    }));
  };

  const removeImage = (index: number) => {
    setFormData(prev => ({
      ...prev,
      images: prev.images.filter((_, i) => i !== index)
    }));
  };

  const updateColors = (colors: string[]) => {
    setFormData(prev => ({
      ...prev,
      colors
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await fetch('/api/products', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        console.log('Product created successfully');
        // Reset form or redirect
      } else {
        console.error('Failed to create product');
      }
    } catch (error) {
      console.error('Error creating product:', error);
    }
  };

  return (
    <div className="new-product-page">
      <h1>Create New Product</h1>
      <form onSubmit={handleSubmit}>
        <ProductForm
          formData={formData}
          updateField={updateField}
          updateSizes={updateSizes}
          addImages={addImages}
          removeImage={removeImage}
          updateColors={updateColors}
        />
        <button type="submit">Create Product</button>
      </form>
    </div>
  );
}