# django-project
STEP 1) CREATE SCHEMA `scadenzario` DEFAULT CHARACTER SET utf8mb4 ;

STEP 2) Eseguire le migrazioni dal progetto con il comando python3 manage.py migrate

STEP3 )Eseguire i seguenti comandi nel query editor di MySQLWorkBench, se disponibile altrimenti 
usa la riga di comando di MySQL.


ALTER TABLE `scadenzario`.`scadenzario_modelricevute` 
DROP FOREIGN KEY `scadenzario_modelric_scadenze_id_78113a0a_fk_scadenzar`;
ALTER TABLE `scadenzario`.`scadenzario_modelricevute` 
ADD CONSTRAINT `scadenzario_modelric_scadenze_id_78113a0a_fk_scadenzar`
  FOREIGN KEY (`scadenze_id`)
  REFERENCES `scadenzario`.`scadenzario_modelscadenze` (`id`)
  ON DELETE CASCADE;



ALTER TABLE `scadenzario`.`scadenzario_modelscadenze` 
DROP FOREIGN KEY `scadenzario_modelsca_idbeneficiario_id_050fa7a1_fk_scadenzar`;
ALTER TABLE `scadenzario`.`scadenzario_modelscadenze` 
ADD CONSTRAINT `scadenzario_modelsca_idbeneficiario_id_050fa7a1_fk_scadenzar`
  FOREIGN KEY (`idbeneficiario_id`)
  REFERENCES `scadenzario`.`scadenzario_modelbeneficiario` (`id`)
  ON DELETE CASCADE;


ALTER TABLE `scadenzario`.`scadenzario_modelricevute` 
CHANGE COLUMN `contentFile` `contentFile` LONGBLOB NOT NULL ;

STEP 4) Installa il certificato che si trova nella cartella python 3.x. in base
alla tua installazione. Normalmente basta fare un doppio click su di esso
# django-project
