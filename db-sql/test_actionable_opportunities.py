#!/usr/bin/env python3
"""
Test script to demonstrate the new actionable trading opportunities focus.
"""

from technical_analysis import TechnicalAnalyzer
from datetime import datetime


def test_actionable_opportunities():
    """Test the new actionable trading opportunities analysis."""
    print("=" * 80)
    print("TESTING ACTIONABLE TRADING OPPORTUNITIES")
    print("=" * 80)
    
    analyzer = TechnicalAnalyzer(verbose=True)
    
    # Setup database
    if not analyzer.setup_database():
        print("❌ Failed to setup database")
        return False
    
    print("\n1. TRADITIONAL APPROACH (All stocks above SMA)")
    print("-" * 50)
    
    # Get all stocks above SMA (traditional approach)
    all_above_sma = analyzer.get_stocks_above_sma(20)
    if all_above_sma is not None:
        print(f"Total stocks above 20-day SMA: {len(all_above_sma)}")
        
        # Show distribution
        extended_stocks = all_above_sma[all_above_sma['percentage_above_sma'] > 8.0]
        moderate_stocks = all_above_sma[
            (all_above_sma['percentage_above_sma'] > 3.0) & 
            (all_above_sma['percentage_above_sma'] <= 8.0)
        ]
        fresh_stocks = all_above_sma[all_above_sma['percentage_above_sma'] <= 3.0]
        
        print(f"• Extended (>8% above): {len(extended_stocks)} stocks - TOO LATE TO ENTER")
        print(f"• Moderate (3-8% above): {len(moderate_stocks)} stocks - RISKY ENTRY")
        print(f"• Fresh (≤3% above): {len(fresh_stocks)} stocks - POTENTIAL ENTRY")
        
        if len(extended_stocks) > 0:
            print(f"\nExtended stocks (avoid these):")
            for _, stock in extended_stocks.head(5).iterrows():
                print(f"  {stock['symbol']}: {stock['percentage_above_sma']:.1f}% above SMA")
    
    print("\n2. NEW ACTIONABLE APPROACH (Near SMA breakouts)")
    print("-" * 50)
    
    # Get actionable opportunities (within ±5% of SMA)
    actionable_opportunities = analyzer.get_stocks_near_sma_breakout(20, 5.0)
    if actionable_opportunities is not None:
        print(f"Total actionable opportunities: {len(actionable_opportunities)}")
        
        # Breakdown by status
        status_counts = actionable_opportunities['breakout_status'].value_counts()
        print(f"\nBreakdown by status:")
        for status, count in status_counts.items():
            emoji = "🟢" if "Above" in status else "🔴" if "Below" in status else "⚪"
            print(f"  {emoji} {status}: {count} stocks")
        
        # Show fresh breakouts (best opportunities)
        fresh_breakouts = actionable_opportunities[
            actionable_opportunities['breakout_status'] == 'Fresh Breakout Above'
        ]
        
        if len(fresh_breakouts) > 0:
            print(f"\n🎯 FRESH BREAKOUTS (Best opportunities):")
            for _, stock in fresh_breakouts.head(5).iterrows():
                print(f"  {stock['symbol']}: {stock['percentage_from_sma']:+.1f}% from SMA - FRESH BREAKOUT!")
        
        # Show stocks near SMA (setup opportunities)
        near_sma = actionable_opportunities[
            actionable_opportunities['percentage_from_sma'].abs() <= 2.0
        ]
        
        if len(near_sma) > 0:
            print(f"\n⚪ NEAR SMA (Setup opportunities):")
            for _, stock in near_sma.head(5).iterrows():
                print(f"  {stock['symbol']}: {stock['percentage_from_sma']:+.1f}% from SMA - WATCH FOR BREAKOUT")
    
    print("\n3. TRADING STRATEGY COMPARISON")
    print("-" * 50)
    
    print("❌ OLD APPROACH:")
    print("  • Includes stocks already extended 8-10% above SMA")
    print("  • Many opportunities already missed")
    print("  • Higher risk entries")
    print("  • Late to the party")
    
    print("\n✅ NEW ACTIONABLE APPROACH:")
    print("  • Focus on stocks within ±5% of SMA")
    print("  • Catch fresh breakouts as they happen")
    print("  • Lower risk entries near support/resistance")
    print("  • Early identification of opportunities")
    
    print("\n4. PRACTICAL TRADING BENEFITS")
    print("-" * 50)
    
    if actionable_opportunities is not None:
        fresh_breakouts = len(actionable_opportunities[
            actionable_opportunities['breakout_status'] == 'Fresh Breakout Above'
        ])
        
        holding_above = len(actionable_opportunities[
            actionable_opportunities['breakout_status'] == 'Holding Above'
        ])
        
        near_sma_count = len(actionable_opportunities[
            actionable_opportunities['percentage_from_sma'].abs() <= 2.0
        ])
        
        print(f"🟢 Fresh Breakouts: {fresh_breakouts} stocks")
        print("   → BUY signal - stocks breaking above SMA today")
        
        print(f"🟡 Holding Above: {holding_above} stocks")
        print("   → MONITOR - stocks maintaining above SMA")
        
        print(f"⚪ Near SMA: {near_sma_count} stocks")
        print("   → WATCH - stocks setting up for potential breakout")
        
        print(f"\nTotal actionable opportunities: {len(actionable_opportunities)}")
        print("vs potentially hundreds of extended stocks to avoid")
    
    print("\n" + "=" * 80)
    print("✅ ACTIONABLE OPPORTUNITIES ANALYSIS COMPLETE!")
    print("The new approach focuses on tradeable setups rather than missed moves.")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        test_actionable_opportunities()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
