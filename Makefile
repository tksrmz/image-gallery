debug:
	IMAGE_GALLERY_ENV_SETTINGS=config/debug_settings.py bash -c 'flask run --debug --host=0.0.0.0'

run:
	IMAGE_GALLERY_ENV_SETTINGS=config/default_settings.py bash -c 'flask run --host=0.0.0.0'
