def db_object(env, db_name, abbr):
    return {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': f'{db_name}_{env("ENV")}',
        'USER': env(f'{abbr}_USER'),
        'PASSWORD': env(f'{abbr}_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': '3306',
    }