'use client'

import { TrendingUp, AlertTriangle, Eye } from 'lucide-react'

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

interface RecommendationCardProps {
  recommendation: Recommendation
}

export default function RecommendationCard({ recommendation }: RecommendationCardProps) {
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
    <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow">
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-3">
              <span className={`inline-flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium border ${getRecommendationColor(recommendation.recommendation)}`}>
                {getRecommendationIcon(recommendation.recommendation)}
                <span>{recommendation.recommendation}</span>
              </span>
              
              <span className={`text-sm font-medium ${getRiskColor(recommendation.risk_level)}`}>
                {recommendation.risk_level} Risk
              </span>
              
              <span className="text-sm text-gray-500">
                {(recommendation.confidence * 100).toFixed(0)}% confidence
              </span>
            </div>
            
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {recommendation.card_name}
            </h3>
            
            <p className="text-gray-600 mb-3">
              {recommendation.rationale}
            </p>
            
            <div className="flex items-center space-x-6 text-sm text-gray-500">
              <span>
                Predicted 3M Return: 
                <span className={`ml-1 font-medium ${recommendation.predicted_return_3m >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {recommendation.predicted_return_3m >= 0 ? '+' : ''}{recommendation.predicted_return_3m.toFixed(1)}%
                </span>
              </span>
              
              {recommendation.price_target_low && recommendation.price_target_high && (
                <span>
                  Target: ${recommendation.price_target_low.toFixed(2)} - ${recommendation.price_target_high.toFixed(2)}
                </span>
              )}
              
              <span>
                Updated: {new Date(recommendation.prediction_date).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}