'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, AlertTriangle, Eye, Search, RefreshCcw } from 'lucide-react'
import axios from 'axios'

interface Recommendation {
  card_id: number
  card_name: string
  recommendation: 'BUY' | 'WATCH' | 'AVOID'
  predicted_return_3m: number
  confidence: number
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH'
  rationale: string
  price_target_low: number | null
  price_target_high: number | null
  prediction_date: string
}

export default function HomePage() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchRecommendations = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await axios.get('/api/tcg/scan')
      setRecommendations(response.data.recommendations || [])
    } catch (err) {
      setError('Failed to fetch recommendations. Make sure the API server is running.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRecommendations()
  }, [])

  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case 'BUY': return 'text-green-600 bg-green-50 border-green-200'
      case 'WATCH': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'AVOID': return 'text-red-600 bg-red-50 border-red-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getRecommendationIcon = (rec: string) => {
    switch (rec) {
      case 'BUY': return <TrendingUp className="w-4 h-4" />
      case 'WATCH': return <Eye className="w-4 h-4" />
      case 'AVOID': return <AlertTriangle className="w-4 h-4" />
      default: return null
    }
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'LOW': return 'text-green-600'
      case 'MEDIUM': return 'text-yellow-600'
      case 'HIGH': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Pokemon Card Investment Dashboard
            </h1>
            <p className="text-gray-600">
              AI-powered market analysis and investment recommendations
            </p>
          </div>
          <button
            onClick={fetchRecommendations}
            disabled={loading}
            className="flex items-center space-x-2 bg-pokemon-blue text-white px-4 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <TrendingUp className="w-8 h-8 text-green-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">BUY Signals</p>
              <p className="text-2xl font-bold text-gray-900">
                {recommendations.filter(r => r.recommendation === 'BUY').length}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <Eye className="w-8 h-8 text-yellow-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">WATCH List</p>
              <p className="text-2xl font-bold text-gray-900">
                {recommendations.filter(r => r.recommendation === 'WATCH').length}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <AlertTriangle className="w-8 h-8 text-red-500" />
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">AVOID Alerts</p>
              <p className="text-2xl font-bold text-gray-900">
                {recommendations.filter(r => r.recommendation === 'AVOID').length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <RefreshCcw className="w-8 h-8 animate-spin mx-auto text-pokemon-blue mb-4" />
          <p className="text-gray-600">Analyzing market data...</p>
        </div>
      )}

      {/* Recommendations */}
      {!loading && recommendations.length === 0 && !error && (
        <div className="text-center py-12">
          <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Recommendations Available</h3>
          <p className="text-gray-600">
            The system needs market data to generate recommendations. 
            <br />
            Make sure the API server is running and has processed some cards.
          </p>
        </div>
      )}

      {!loading && recommendations.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Current Recommendations</h2>
          
          {recommendations.map((rec, index) => (
            <div key={index} className="bg-white rounded-lg shadow hover:shadow-md transition-shadow">
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-3">
                      <span className={`inline-flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium border ${getRecommendationColor(rec.recommendation)}`}>
                        {getRecommendationIcon(rec.recommendation)}
                        <span>{rec.recommendation}</span>
                      </span>
                      
                      <span className={`text-sm font-medium ${getRiskColor(rec.risk_level)}`}>
                        {rec.risk_level} Risk
                      </span>
                      
                      <span className="text-sm text-gray-500">
                        {(rec.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                    
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {rec.card_name}
                    </h3>
                    
                    <p className="text-gray-600 mb-3">
                      {rec.rationale}
                    </p>
                    
                    <div className="flex items-center space-x-6 text-sm text-gray-500">
                      <span>
                        Predicted 3M Return: 
                        <span className={`ml-1 font-medium ${rec.predicted_return_3m >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {rec.predicted_return_3m >= 0 ? '+' : ''}{rec.predicted_return_3m.toFixed(1)}%
                        </span>
                      </span>
                      
                      {rec.price_target_low && rec.price_target_high && (
                        <span>
                          Target: ${rec.price_target_low.toFixed(2)} - ${rec.price_target_high.toFixed(2)}
                        </span>
                      )}
                      
                      <span>
                        Updated: {new Date(rec.prediction_date).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="mt-12 text-center text-gray-500 text-sm">
        <p>⚠️ This is for educational purposes only. Not financial advice.</p>
        <p className="mt-1">Always do your own research before making investment decisions.</p>
      </div>
    </div>
  )
}