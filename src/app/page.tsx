import Link from 'next/link'

export default function Home() {
  return (
    <main className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">AC9 Sport API - Admin Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Link 
          href="/account/admin/products/new" 
          className="block p-6 bg-white rounded-lg border border-gray-200 shadow-md hover:bg-gray-50"
        >
          <h2 className="text-xl font-semibold mb-2">Add New Product</h2>
          <p className="text-gray-600">Create a new product in the catalog</p>
        </Link>
        
        <div className="block p-6 bg-white rounded-lg border border-gray-200 shadow-md">
          <h2 className="text-xl font-semibold mb-2">Manage Products</h2>
          <p className="text-gray-600">View and edit existing products</p>
        </div>
        
        <div className="block p-6 bg-white rounded-lg border border-gray-200 shadow-md">
          <h2 className="text-xl font-semibold mb-2">Categories</h2>
          <p className="text-gray-600">Manage product categories</p>
        </div>
      </div>
    </main>
  )
}