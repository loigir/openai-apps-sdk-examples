import { useEffect, useState, useCallback, useMemo } from "react";
import { useOpenAiGlobal } from "../use-openai-global";
import { useWidgetState } from "../use-widget-state";
import PickupCard from "./pickup-card";
import EmergencyAlert from "./emergency-alert";
import { sanitizeText } from "../utils/sanitize";
import "./dashboard.css";

export default function Dashboard() {
  const toolOutput = useOpenAiGlobal("toolOutput");
  const metadata = useOpenAiGlobal("toolResponseMetadata");

  const [state, setState] = useWidgetState({
    view: "timeline", // 'timeline' | 'list' | 'grid'
    filter: "all", // 'all' | 'next_30min' | 'delays'
    alert: null,
  });

  const [currentTime, setCurrentTime] = useState(new Date());
  const [realtimePickups, setRealtimePickups] = useState([]);

  const pickups = metadata?.pickups || realtimePickups || [];
  const schoolInfo = metadata?.school_info || {
    name: "École AllôBye",
    id: "school_1",
  };
  const refreshInterval = metadata?.refresh_interval || 30;

  // Update current time every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Auto-refresh data from MCP tool
  useEffect(() => {
    if (!schoolInfo?.id) return;

    const interval = setInterval(() => {
      // Call MCP tool to refresh data
      if (window.openai?.callTool) {
        window.openai
          .callTool("school-dashboard-fetch", {
            schoolId: schoolInfo.id,
            timeWindow: "current",
          })
          .catch((err) => console.error("Error refreshing dashboard:", err));
      }
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [schoolInfo, refreshInterval]);

  // Supabase real-time subscriptions
  useEffect(() => {
    if (!schoolInfo?.id) return;

    const setupRealtimeSubscription = async () => {
      try {
        const { createClient } = await import("@supabase/supabase-js");
        const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
        const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

        if (!supabaseUrl || !supabaseKey) {
          console.warn("Supabase credentials not configured");
          return;
        }

        const supabase = createClient(supabaseUrl, supabaseKey);

        // Subscribe to pickups table
        const channel = supabase
          .channel("pickups-changes")
          .on(
            "postgres_changes",
            {
              event: "*",
              schema: "public",
              table: "pickups",
              filter: `school_id=eq.${schoolInfo.id}`,
            },
            (payload) => {
              console.log("Pickup change received:", payload);

              if (payload.eventType === "INSERT" || payload.eventType === "UPDATE") {
                // Refresh pickup list
                setRealtimePickups((prev) => {
                  const updated = prev.filter((p) => p.id !== payload.new.id);
                  return [...updated, payload.new].sort(
                    (a, b) => new Date(a.scheduled_time) - new Date(b.scheduled_time)
                  );
                });
              } else if (payload.eventType === "DELETE") {
                setRealtimePickups((prev) => prev.filter((p) => p.id !== payload.old.id));
              }
            }
          )
          .subscribe();

        // Subscribe to emergencies
        const emergencyChannel = supabase
          .channel("emergencies-changes")
          .on(
            "postgres_changes",
            {
              event: "INSERT",
              schema: "public",
              table: "emergencies",
            },
            (payload) => {
              console.log("Emergency received:", payload);
              setState((prev) => ({
                ...prev,
                alert: {
                  type: payload.new.emergency_type,
                  context: payload.new.context,
                  child_id: payload.new.child_id,
                },
              }));

              // Auto-clear alert after 30 seconds
              setTimeout(() => {
                setState((prev) => ({ ...prev, alert: null }));
              }, 30000);
            }
          )
          .subscribe();

        return () => {
          channel.unsubscribe();
          emergencyChannel.unsubscribe();
        };
      } catch (error) {
        console.error("Error setting up real-time subscription:", error);
      }
    };

    const cleanup = setupRealtimeSubscription();
    return () => {
      cleanup?.then((fn) => fn?.());
    };
  }, [schoolInfo?.id, setState]);

  // Filter pickups based on current filter - memoized to avoid recalculation
  const filteredPickups = useMemo(() => {
    return pickups.filter((pickup) => {
      if (state.filter === "all") return true;

      if (state.filter === "next_30min") {
        const scheduledTime = new Date(pickup.scheduled_time);
        const thirtyMinutesFromNow = new Date(currentTime.getTime() + 30 * 60 * 1000);
        return scheduledTime <= thirtyMinutesFromNow;
      }

      if (state.filter === "delays") {
        return pickup.delay && pickup.delay > 0;
      }

      return true;
    });
  }, [pickups, state.filter, currentTime]);

  const handleCloseAlert = useCallback(() => {
    setState((prev) => ({ ...prev, alert: null }));
  }, [setState]);

  const handleViewChange = useCallback((view) => {
    setState((prev) => ({ ...prev, view }));
  }, [setState]);

  const handleFilterChange = useCallback((filter) => {
    setState((prev) => ({ ...prev, filter }));
  }, [setState]);

  return (
    <div className="allobye-dashboard fullscreen">
      <header className="dashboard-header">
        <div className="header-left">
          <h1>{sanitizeText(schoolInfo?.name)}</h1>
          <div className="pickup-count">
            {filteredPickups.length} ramassage{filteredPickups.length !== 1 ? "s" : ""}
          </div>
        </div>
        <div className="header-right">
          <time className="current-time">
            {currentTime.toLocaleTimeString("fr-CA", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </time>
          <div className="current-date">
            {currentTime.toLocaleDateString("fr-CA", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </div>
        </div>
      </header>

      {state.alert && <EmergencyAlert alert={state.alert} onClose={handleCloseAlert} />}

      <section className={`pickup-queue view-${state.view}`}>
        {filteredPickups.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <p>Aucun ramassage prévu pour le moment</p>
          </div>
        ) : (
          filteredPickups.map((pickup) => <PickupCard key={pickup.id} pickup={pickup} currentTime={currentTime} />)
        )}
      </section>

      <footer className="dashboard-footer">
        <div className="view-controls">
          <button
            className={state.view === "timeline" ? "active" : ""}
            onClick={() => handleViewChange("timeline")}
          >
            Timeline
          </button>
          <button className={state.view === "list" ? "active" : ""} onClick={() => handleViewChange("list")}>
            Liste
          </button>
          <button className={state.view === "grid" ? "active" : ""} onClick={() => handleViewChange("grid")}>
            Grille
          </button>
        </div>

        <div className="filter-controls">
          <button
            className={state.filter === "all" ? "active" : ""}
            onClick={() => handleFilterChange("all")}
          >
            Tous
          </button>
          <button
            className={state.filter === "next_30min" ? "active" : ""}
            onClick={() => handleFilterChange("next_30min")}
          >
            30 min
          </button>
          <button
            className={state.filter === "delays" ? "active" : ""}
            onClick={() => handleFilterChange("delays")}
          >
            Retards
          </button>
        </div>

        <div className="status-indicator">
          <span className="status-dot online"></span>
          Connecté
        </div>
      </footer>
    </div>
  );
}
