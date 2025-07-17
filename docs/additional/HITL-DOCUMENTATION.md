# Human-in-the-Loop (HITL) Implementation Guide

## Overview

This document outlines a potential future implementation of Human-in-the-Loop (HITL) approval processes for the Smart-0DTE and Mag7-7DTE systems. While the current implementation remains fully autonomous, this guide serves as a reference for adding human oversight if required in the future.

## Rationale for HITL

Human-in-the-Loop systems can provide several benefits:
- Quality control for high-value trades
- Adaptability to unusual market conditions
- Regulatory compliance in certain jurisdictions
- Psychological comfort for users new to algorithmic trading
- Learning opportunities for users to understand system logic

## Tiered Autonomy Implementation

### Tier Structure

1. **Tier 1: Fully Autonomous (Default)**
   - Trades below a certain size threshold (e.g., 50% of max position size)
   - High-confidence signals (e.g., confidence score > 0.85)
   - Standard market conditions (VIX below threshold, normal trading hours)

2. **Tier 2: Approval Required**
   - Larger position sizes (e.g., >50% of maximum)
   - Medium-confidence signals (e.g., 0.70-0.85 confidence)
   - Unusual market conditions (high VIX, Fed announcement days)
   - New strategies or instruments being tested

3. **Tier 3: Enhanced Approval**
   - Maximum position sizes
   - Correlated positions that increase sector exposure
   - Market conditions with elevated risk (extreme VIX readings)
   - Overnight positions in 7DTE system with pending news/earnings

### Database Schema Changes

```sql
-- Add to Signal model
ALTER TABLE signals ADD COLUMN requires_approval BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE signals ADD COLUMN approval_tier INTEGER NOT NULL DEFAULT 1;
ALTER TABLE signals ADD COLUMN approved_by_user_id INTEGER REFERENCES users(id);
ALTER TABLE signals ADD COLUMN approval_time TIMESTAMP;
ALTER TABLE signals ADD COLUMN approval_notes TEXT;

-- Add to UserPreference model
ALTER TABLE user_preferences ADD COLUMN enable_approval BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE user_preferences ADD COLUMN tier1_threshold FLOAT NOT NULL DEFAULT 0.5;
ALTER TABLE user_preferences ADD COLUMN tier2_threshold FLOAT NOT NULL DEFAULT 0.8;
ALTER TABLE user_preferences ADD COLUMN approval_timeout_minutes INTEGER NOT NULL DEFAULT 30;
```

### Code Modifications

#### Signal Generation Service

```python
async def generate_signal(self, instrument_id, signal_type, confidence_score, **kwargs):
    """Generate a trading signal with appropriate approval tier."""
    # Create signal
    signal = Signal(
        instrument_id=instrument_id,
        signal_type=signal_type,
        confidence_score=confidence_score,
        # ... other fields
    )
    
    # Determine approval tier
    approval_tier = self._determine_approval_tier(
        confidence_score=confidence_score,
        position_size=kwargs.get('position_size', 0),
        market_conditions=kwargs.get('market_conditions', {})
    )
    
    # Set approval requirements
    if approval_tier > 1:
        signal.requires_approval = True
        signal.approval_tier = approval_tier
        signal.status = SignalStatus.PENDING_APPROVAL
    else:
        signal.requires_approval = False
        signal.approval_tier = 1
        signal.status = SignalStatus.ACTIVE
    
    # Save signal
    self.db.add(signal)
    self.db.commit()
    self.db.refresh(signal)
    
    # If approval required, send notification
    if signal.requires_approval:
        await self._send_approval_notification(signal)
    
    return signal

def _determine_approval_tier(self, confidence_score, position_size, market_conditions):
    """Determine the approval tier based on signal characteristics."""
    # Get user preferences
    user_prefs = self.db.query(UserPreference).first()
    tier1_threshold = user_prefs.tier1_threshold if user_prefs else 0.5
    tier2_threshold = user_prefs.tier2_threshold if user_prefs else 0.8
    
    # Check position size
    max_position_size = self.risk_limits.max_position_size
    position_size_ratio = position_size / max_position_size if max_position_size > 0 else 0
    
    # Check market conditions
    vix_level = market_conditions.get('vix_level', 20)
    is_high_volatility = vix_level > 30
    is_unusual_market = market_conditions.get('is_unusual', False)
    
    # Determine tier
    if position_size_ratio > 0.8 or is_high_volatility:
        return 3  # Enhanced approval
    elif position_size_ratio > tier1_threshold or confidence_score < tier2_threshold or is_unusual_market:
        return 2  # Standard approval
    else:
        return 1  # Fully autonomous
```

#### IBKR Service

```python
async def _should_execute_signal(self, signal: Dict[str, Any]) -> bool:
    """Determine if a signal should be executed."""
    try:
        # Check if already executed
        signal_id = signal.get('id', '')
        if signal_id in [order.get('signal_id') for order in self.active_orders.values()]:
            return False
        
        # Check approval status
        if signal.get('requires_approval', False) and not signal.get('approved_by_user_id'):
            # Check if approval has timed out
            user_prefs = self.db.query(UserPreference).first()
            timeout_minutes = user_prefs.approval_timeout_minutes if user_prefs else 30
            
            generation_time = signal.get('generation_time')
            if generation_time:
                time_diff = (datetime.utcnow() - generation_time).total_seconds() / 60
                if time_diff > timeout_minutes:
                    # Update signal status to expired
                    await self._expire_signal(signal_id)
                    return False
            
            # Awaiting approval
            return False
        
        # Other checks (rate limiting, account requirements, market hours)
        # ...
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking signal execution: {e}")
        return False

async def _expire_signal(self, signal_id):
    """Mark a signal as expired due to approval timeout."""
    try:
        signal = self.db.query(Signal).filter(Signal.id == signal_id).first()
        if signal:
            signal.status = SignalStatus.EXPIRED
            self.db.commit()
            logger.info(f"Signal {signal_id} expired due to approval timeout")
    except Exception as e:
        logger.error(f"Error expiring signal: {e}")
```

### API Endpoints

```python
@router.get("/signals/pending-approval", response_model=List[SignalResponse])
def get_pending_approval_signals(
    tier: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get signals pending approval."""
    query = db.query(Signal).filter(
        Signal.requires_approval == True,
        Signal.approved_by_user_id.is_(None),
        Signal.status == SignalStatus.PENDING_APPROVAL
    )
    
    if tier:
        query = query.filter(Signal.approval_tier == tier)
    
    # Order by tier (highest first) and then by generation time
    query = query.order_by(Signal.approval_tier.desc(), Signal.generation_time.asc())
    
    return query.all()

@router.post("/signals/{signal_id}/approve", response_model=SignalResponse)
def approve_signal(
    signal_id: int,
    approval_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a signal for execution."""
    # Check user permissions
    if current_user.role not in [UserRole.ADMIN, UserRole.TRADER]:
        raise HTTPException(status_code=403, detail="Not authorized to approve signals")
    
    # Get signal
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal with ID {signal_id} not found")
    
    # Check if signal requires approval
    if not signal.requires_approval:
        raise HTTPException(status_code=400, detail="Signal does not require approval")
    
    # Check if already approved
    if signal.approved_by_user_id:
        raise HTTPException(status_code=400, detail="Signal already approved")
    
    # Approve signal
    signal.approved_by_user_id = current_user.id
    signal.approval_time = datetime.utcnow()
    signal.approval_notes = approval_notes
    signal.status = SignalStatus.ACTIVE
    
    # Commit changes
    db.commit()
    db.refresh(signal)
    
    # Log activity
    activity_log = ActivityLog(
        user_id=current_user.id,
        activity_type="signal_approval",
        description=f"Approved signal {signal_id}",
        related_entity_type="signal",
        related_entity_id=signal_id
    )
    db.add(activity_log)
    db.commit()
    
    return signal

@router.post("/signals/{signal_id}/reject", response_model=SignalResponse)
def reject_signal(
    signal_id: int,
    rejection_reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a signal."""
    # Similar implementation to approve_signal, but sets status to CANCELLED
    # ...
```

### User Interface Components

#### Approval Dashboard

The approval dashboard would include:

1. **Pending Approvals Queue**
   - List of signals requiring approval
   - Sorted by tier and time sensitivity
   - Color-coded by approval tier
   - Countdown timers for expiration

2. **Signal Details Panel**
   - Complete signal information
   - Strategy visualization
   - Risk metrics and position sizing
   - Market context

3. **Action Buttons**
   - Approve button
   - Reject button
   - Modify parameters button (for adjusting position size)
   - Notes field for documenting decision rationale

#### Mobile Notifications

For traders on the go:

1. **Push Notifications**
   - Tier-based urgency levels
   - Direct deep links to approval screen
   - Quick approve/reject actions

2. **Email Alerts**
   - Detailed signal information
   - Secure approval links
   - Expiration warnings

## Potential Challenges

1. **Decision Fatigue**
   - Too many approval requests could lead to rubber-stamping
   - Solution: Carefully calibrate tier thresholds

2. **Availability Constraints**
   - Users may not always be available during market hours
   - Solution: Implement delegation and backup approvers

3. **Psychological Attachment**
   - Users may become overly attached to monitoring the system
   - Solution: Implement "approval-free days" to break the habit

4. **Performance Impact**
   - Approval delays could impact strategy performance
   - Solution: Conduct A/B testing to measure impact

## Conclusion

While the current implementation remains fully autonomous, this HITL framework provides a blueprint for adding human oversight if required in the future. The tiered approach balances efficiency with control, allowing for human judgment where it adds the most value while maintaining automation for routine decisions.

