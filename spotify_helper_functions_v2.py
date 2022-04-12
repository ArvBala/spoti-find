
import pandas as pd
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials #To access authorised Spotify data
import spotipy.util as util
import json
import pprint

def get_spotify_token(client_id, client_secret, username, scope='playlist-modify-public user-library-read',redirect_uri='http://localhost:7778/callback'):

	token_obj = util.prompt_for_user_token(
	    username=username, 
	    scope=scope, 
	    client_id=client_id,   
	    client_secret=client_secret,
	    redirect_uri=redirect_uri
	)
	return token_obj

def get_my_library(token):

    user_saved_tracks = []
    get_next_track_set = True
    offset = 0
    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    while get_next_track_set == True:
        params = {'limit' : 50, 'offset' : offset}
        response = requests.get('https://api.spotify.com/v1/me/tracks', headers=headers, params=params)
        tracks_in_set = json.loads(response.text)
        tracks_in_set = tracks_in_set['items']
        if len(tracks_in_set) > 0:
            user_saved_tracks = user_saved_tracks + tracks_in_set
            offset = offset + 50
        elif len(tracks_in_set) == 0:
            get_next_track_set = False
            
    saved_tracks_formatted = []
    for obj in user_saved_tracks:
        added_at = obj['added_at']
        track = obj['track']
        
        track_formatted = {
            'track_id' : track['id'],
            'saved_at' : added_at,
            'track_name' : track['name'],
            'primary_artist_id' : track['artists'][0]['id'],
            'all_artists' : [artist['id'] for artist in track['artists']],
            'album_id' : track['album']['id'],
            'duration_ms' : track['duration_ms'],
            'is_explicit' : track['explicit'],
            'popularity': track['popularity'],
            'track_number' : track['track_number']
        }
        saved_tracks_formatted.append(track_formatted)
        
    saved_tracks_df = pd.DataFrame(saved_tracks_formatted)
    list_of_track_ids = list(saved_tracks_df['track_id'])
    
    all_track_features = []
    lower_bound = 0
    upper_bound = 99
    for interval in range(0,len(list_of_track_ids),100):
        tracks_to_get_features = list_of_track_ids[lower_bound:upper_bound]
        tracks_string = ','.join(tracks_to_get_features)
        track_features = requests.get('https://api.spotify.com/v1/audio-features/', headers=headers, params={'ids': tracks_string})
        status_code = track_features.status_code
        while status_code == 503:
            track_features = requests.get('https://api.spotify.com/v1/audio-features/', headers=headers, params={'ids': tracks_string})
            status_code = track_features.status_code
        track_features = json.loads(track_features.text)['audio_features']
        all_track_features = all_track_features + track_features
        lower_bound = upper_bound
        upper_bound += 100
    
    track_features_df = pd.DataFrame(all_track_features)
    
    saved_tracks_df = saved_tracks_df.merge(track_features_df, how='left', left_on='track_id', right_on='id')
    
    saved_tracks_df = saved_tracks_df[
        [
            'album_id', 'all_artists', 'duration_ms_x', 'is_explicit', 'popularity',
            'primary_artist_id', 'track_id', 'track_name', 'track_number',
            'acousticness', 'danceability','energy', 'instrumentalness', 
            'key', 'liveness', 'loudness','mode', 'speechiness', 'tempo', 
            'time_signature', 'valence','saved_at'
        ]
    ]
    
    saved_tracks_df = saved_tracks_df.rename(columns={'duration_ms_x' : 'duration_ms'})
    
    saved_tracks_df = saved_tracks_df[['track_id','saved_at','track_name','primary_artist_id','all_artists','album_id','track_number','duration_ms','popularity','is_explicit','acousticness','danceability','energy','instrumentalness','key','liveness','loudness','mode','speechiness','tempo','time_signature','valence']]
    
    return saved_tracks_df

def get_playlist_audio_features(playlist_id, token):

	headers = {
    'Authorization': 'Bearer {}'.format(token)
    }

	response = requests.get('https://api.spotify.com/v1/playlists/{}'.format(playlist_id), headers=headers)

	playlist_obj = json.loads(response.text)
	tracks = playlist_obj['tracks']
	track_ids = []
	for track in tracks['items']:
		track_ids.append(track['track']['id'])

	all_track_features = []
	lower_bound = 0
	upper_bound = 99
	for interval in range(0,len(track_ids),100):
	    tracks_to_get_features = track_ids[lower_bound:upper_bound]
	    tracks_string = ','.join(tracks_to_get_features)
	    track_features = requests.get('https://api.spotify.com/v1/audio-features/', headers=headers, params={'ids': tracks_string})
	    status_code = track_features.status_code
	    while status_code == 503:
	        track_features = requests.get('https://api.spotify.com/v1/audio-features/', headers=headers, params={'ids': tracks_string})
	        status_code = track_features.status_code
	    track_features = json.loads(track_features.text)['audio_features']
	    all_track_features = all_track_features + track_features
	    lower_bound = upper_bound
	    upper_bound += 100

	track_features_df = pd.DataFrame(all_track_features)
	return track_features_df

def add_tracks_to_playlist(playlist_id,track_uris,token):
	headers = {
    'Authorization': 'Bearer {}'.format(token),
    'Content-Type' : 'application/json'
	}

	json = {
	    'uris' : track_uris
	}
	response = requests.post('https://api.spotify.com/v1/playlists/{}/tracks'.format(playlist_id), headers=headers, json=json)
	
	return response.text

def create_new_playlist(user_id,token,playlist_name, public=True, collaborative=False):
	headers = {
	    'Authorization': 'Bearer {}'.format(token),
	}
	params = {
	  'name' : playlist_name,
	  'public' : public,
	  'collaborative' : collaborative
	}

	response = requests.post('https://api.spotify.com/v1/users/{}/playlists'.format(user_id), headers=headers, json=params)

	response_json = json.loads(response.text)
	playlist_id = response_json['id']

	return response_json