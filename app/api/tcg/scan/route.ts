import { NextResponse } from 'next/server'

export async function GET() {
  try {
    // Get the API URL - use Railway URL if available, otherwise localhost
    const apiUrl = process.env.API_URL || 'http://localhost:8000'
    
    const response = await fetch(`${apiUrl}/tcg/scan`)
    
    if (!response.ok) {
      throw new Error(`API responded with status: ${response.status}`)
    }
    
    const data = await response.json()
    return NextResponse.json(data)
    
  } catch (error) {
    console.error('Failed to fetch from TCG API:', error)
    
    // Return mock data if API is unavailable
    const mockData = {
      message: "Using mock data (API unavailable)",
      timestamp: new Date().toISOString(),
      recommendations: [
        {
          card_id: 1,
          card_name: "Charizard VMAX (Champion's Path)",
          recommendation: "BUY",
          predicted_return_3m: 15.5,
          confidence: 0.87,
          risk_level: "MEDIUM",
          rationale: "Strong demand from collectors, limited print run, popular Pokemon. Price has stabilized after initial drop.",
          price_target_low: 332.50,
          price_target_high: 402.50,
          prediction_date: new Date().toISOString()
        },
        {
          card_id: 3,
          card_name: "Umbreon VMAX (Evolving Skies)",
          recommendation: "BUY", 
          predicted_return_3m: 22.3,
          confidence: 0.91,
          risk_level: "MEDIUM",
          rationale: "Extremely popular card with strong artwork. Recent dip provides good entry point.",
          price_target_low: 266.00,
          price_target_high: 322.00,
          prediction_date: new Date().toISOString()
        }
      ]
    }
    
    return NextResponse.json(mockData)
  }
}