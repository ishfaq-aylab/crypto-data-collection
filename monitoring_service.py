#!/usr/bin/env python3
"""Monitoring service for collecting metrics and health status."""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from loguru import logger

from interfaces import IMonitoringService


class MonitoringService(IMonitoringService):
    """Monitoring service for metrics and health tracking."""
    
    def __init__(self, max_metrics_history: int = 1000):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics_history))
        self._events: List[Dict[str, Any]] = []
        self._health_status: Dict[str, Any] = {}
        self._start_time = datetime.now()
        self._max_events = 1000
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a metric."""
        try:
            metric_data = {
                "timestamp": datetime.now(),
                "value": value,
                "tags": tags or {}
            }
            self._metrics[name].append(metric_data)
            
            logger.debug(f"📊 Metric recorded: {name}={value}")
            
        except Exception as e:
            logger.error(f"❌ Error recording metric {name}: {e}")
    
    def record_event(self, event: str, data: Dict[str, Any] = None) -> None:
        """Record an event."""
        try:
            event_data = {
                "timestamp": datetime.now(),
                "event": event,
                "data": data or {}
            }
            
            self._events.append(event_data)
            
            # Keep only recent events
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
            
            logger.debug(f"📝 Event recorded: {event}")
            
        except Exception as e:
            logger.error(f"❌ Error recording event {event}: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        try:
            now = datetime.now()
            uptime = (now - self._start_time).total_seconds()
            
            # Calculate health metrics
            total_metrics = sum(len(metrics) for metrics in self._metrics.values())
            recent_events = len([e for e in self._events 
                               if (now - e["timestamp"]).total_seconds() < 300])  # Last 5 minutes
            
            # Check for error events
            error_events = len([e for e in self._events 
                              if "error" in e["event"].lower() and 
                              (now - e["timestamp"]).total_seconds() < 300])
            
            health_score = 100
            if error_events > 0:
                health_score -= min(error_events * 10, 50)  # Reduce health for errors
            
            if recent_events == 0 and uptime > 60:
                health_score -= 20  # Reduce health if no recent activity
            
            status = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy"
            
            self._health_status = {
                "status": status,
                "health_score": health_score,
                "uptime_seconds": uptime,
                "total_metrics": total_metrics,
                "recent_events": recent_events,
                "error_events": error_events,
                "last_updated": now,
                "metrics_count": len(self._metrics),
                "events_count": len(self._events)
            }
            
            return self._health_status
            
        except Exception as e:
            logger.error(f"❌ Error getting health status: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        try:
            summary = {}
            now = datetime.now()
            
            for metric_name, metric_data in self._metrics.items():
                if not metric_data:
                    continue
                
                values = [m["value"] for m in metric_data]
                recent_values = [m["value"] for m in metric_data 
                               if (now - m["timestamp"]).total_seconds() < 300]  # Last 5 minutes
                
                summary[metric_name] = {
                    "count": len(values),
                    "recent_count": len(recent_values),
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "avg": sum(values) / len(values) if values else 0,
                    "recent_avg": sum(recent_values) / len(recent_values) if recent_values else 0,
                    "last_value": values[-1] if values else 0,
                    "last_timestamp": metric_data[-1]["timestamp"] if metric_data else None
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error getting metrics summary: {e}")
            return {"error": str(e)}
    
    def get_recent_events(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent events."""
        try:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            return [e for e in self._events if e["timestamp"] >= cutoff]
            
        except Exception as e:
            logger.error(f"❌ Error getting recent events: {e}")
            return []
    
    def get_metric_trend(self, metric_name: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metric trend over time."""
        try:
            if metric_name not in self._metrics:
                return []
            
            cutoff = datetime.now() - timedelta(minutes=minutes)
            return [m for m in self._metrics[metric_name] if m["timestamp"] >= cutoff]
            
        except Exception as e:
            logger.error(f"❌ Error getting metric trend for {metric_name}: {e}")
            return []
    
    def clear_old_data(self, hours: int = 24) -> None:
        """Clear old metrics and events."""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            # Clear old metrics
            for metric_name in list(self._metrics.keys()):
                self._metrics[metric_name] = deque(
                    [m for m in self._metrics[metric_name] if m["timestamp"] >= cutoff],
                    maxlen=self._metrics[metric_name].maxlen
                )
            
            # Clear old events
            self._events = [e for e in self._events if e["timestamp"] >= cutoff]
            
            logger.info(f"🧹 Cleared data older than {hours} hours")
            
        except Exception as e:
            logger.error(f"❌ Error clearing old data: {e}")


# Global monitoring service instance
monitoring_service = MonitoringService()


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    return monitoring_service
