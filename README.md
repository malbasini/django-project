# django-project
STEP 1) CREATE SCHEMA `scadenzario` DEFAULT CHARACTER SET utf8 ;

STEP 2) Eseguire le migrazioni dal progetto con makemigrations e migrate

STEP3 )Eseguire i seguenti comandi nel query editor di MySQLWorkBench


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

