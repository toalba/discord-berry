from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os

app = Flask(__name__)
CONFIG_FILE = 'tournament_config.json'

def load_config():
    """Load tournament configuration from JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"tournaments": []}

def save_config(config):
    """Save tournament configuration to JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

@app.route('/')
def index():
    """Main page showing all tournaments."""
    config = load_config()
    return render_template('index.html', tournaments=config['tournaments'])

@app.route('/tournament/<tournament_id>')
def view_tournament(tournament_id):
    """View/edit a specific tournament."""
    config = load_config()
    tournament = next((t for t in config['tournaments'] if t['id'] == tournament_id), None)
    if not tournament:
        return "Tournament not found", 404
    return render_template('tournament.html', tournament=tournament)

@app.route('/tournament/new', methods=['GET', 'POST'])
def new_tournament():
    """Create a new tournament."""
    if request.method == 'POST':
        config = load_config()
        new_tournament = {
            "id": request.form['id'],
            "name": request.form['name'],
            "mappool": [],
            "stages": {}
        }
        config['tournaments'].append(new_tournament)
        save_config(config)
        return redirect(url_for('view_tournament', tournament_id=new_tournament['id']))
    return render_template('new_tournament.html')

@app.route('/api/tournament/<tournament_id>/mappool', methods=['POST'])
def update_mappool(tournament_id):
    """Update mappool for a tournament."""
    config = load_config()
    tournament = next((t for t in config['tournaments'] if t['id'] == tournament_id), None)
    if not tournament:
        return jsonify({"error": "Tournament not found"}), 404
    
    data = request.json
    tournament['mappool'] = data.get('mappool', [])
    save_config(config)
    return jsonify({"success": True})

@app.route('/api/tournament/<tournament_id>/stage', methods=['POST'])
def add_or_update_stage(tournament_id):
    """Add or update a stage in a tournament."""
    config = load_config()
    tournament = next((t for t in config['tournaments'] if t['id'] == tournament_id), None)
    if not tournament:
        return jsonify({"error": "Tournament not found"}), 404
    
    data = request.json
    stage_name = data.get('stage_name')
    if not stage_name:
        return jsonify({"error": "Stage name required"}), 400
    
    tournament['stages'][stage_name] = {
        "map_bans": int(data.get('map_bans', 0)),
        "map_picks": int(data.get('map_picks', 1)),
        "ship_bans": int(data.get('ship_bans', 0)),
        "has_tiebreaker": data.get('has_tiebreaker', False),
        "tiebreaker_maps": data.get('tiebreaker_maps', [])
    }
    save_config(config)
    return jsonify({"success": True})

@app.route('/api/tournament/<tournament_id>/stage/<stage_name>', methods=['DELETE'])
def delete_stage(tournament_id, stage_name):
    """Delete a stage from a tournament."""
    config = load_config()
    tournament = next((t for t in config['tournaments'] if t['id'] == tournament_id), None)
    if not tournament:
        return jsonify({"error": "Tournament not found"}), 404
    
    if stage_name in tournament['stages']:
        del tournament['stages'][stage_name]
        save_config(config)
        return jsonify({"success": True})
    return jsonify({"error": "Stage not found"}), 404

@app.route('/api/tournament/<tournament_id>', methods=['DELETE'])
def delete_tournament(tournament_id):
    """Delete a tournament."""
    config = load_config()
    config['tournaments'] = [t for t in config['tournaments'] if t['id'] != tournament_id]
    save_config(config)
    return jsonify({"success": True})

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
