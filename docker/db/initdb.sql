-- Solo alla prima creazione del volume: un database separato per i test del backend,
-- così pytest non tocca mai i dati (sintetici) dell'ambiente di sviluppo.
CREATE DATABASE esposti_test OWNER esposti;
