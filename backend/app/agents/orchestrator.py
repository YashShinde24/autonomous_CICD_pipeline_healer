from datetime import datetime
from app.agents.graph_builder import build_graph
from app.core.results_writer import save_results

def run_pipeline(state):

    state["start_time"] = datetime.utcnow().isoformat()

    graph = build_graph()

    final_state = graph.invoke(state)

    final_state["end_time"] = datetime.utcnow().isoformat()

    final_state = save_results(final_state)

    return final_state
