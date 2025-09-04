// Size stock interfaces for product management

export interface SizeStock {
  size: string;
  stock: number;
}

export interface EuroSizeStock {
  euro_size: string;
  stock: number;
}

export interface ProductFormData {
  name: string;
  description: string;
  price: number;
  sizes: SizeStock[];
  colors: string[];
  images: string[];
  isActive: boolean;
  isFeatured: boolean;
}

export type UpdateSizesFunction = (updatedSizes: SizeStock[]) => void;
export type UpdateEuroSizesFunction = (sizes: EuroSizeStock[]) => void;