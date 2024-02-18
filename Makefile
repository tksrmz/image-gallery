dummy:
	IMAGE_GALLERY_ENV_SETTINGS=config/dummy_settings.py bash -c 'flask run --debug --host=0.0.0.0'

debug:
	IMAGE_GALLERY_ENV_SETTINGS=config/default_settings.py bash -c 'flask run --debug --host=0.0.0.0'
