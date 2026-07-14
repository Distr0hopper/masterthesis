import { MigrationInterface, QueryRunner } from "typeorm";

export class Migration1782134708534 implements MigrationInterface {
    name = 'Migration1782134708534'

    public async up(queryRunner: QueryRunner): Promise<void> {
        await queryRunner.query(`CREATE TYPE "public"."components_source_enum" AS ENUM('automated_packaging', 'manual_upload')`);
        await queryRunner.query(`CREATE TABLE "components" ("id" uuid NOT NULL DEFAULT uuid_generate_v4(), "name" character varying NOT NULL, "authorName" character varying, "description" character varying, "repoUrl" character varying, "repoCommitSha" character varying, "doi" character varying, "version" integer NOT NULL DEFAULT 1, "cwlContent" text NOT NULL, "source" "public"."components_source_enum" NOT NULL DEFAULT 'manual_upload', "domain" character varying NOT NULL, "createdAt" TIMESTAMP NOT NULL DEFAULT now(), "updatedAt" TIMESTAMP NOT NULL DEFAULT now(), "created_by_id" uuid, CONSTRAINT "UQ_components_name_version" UNIQUE ("name", "version"), CONSTRAINT "PK_0d742661c63926321b5f5eac1ad" PRIMARY KEY ("id"))`);
        await queryRunner.query(`CREATE UNIQUE INDEX "UQ_components_name_commitsha" ON "components" ("name", "repoCommitSha") WHERE "repoCommitSha" IS NOT NULL`);
        await queryRunner.query(`CREATE TYPE "public"."parameters_direction_enum" AS ENUM('input', 'output')`);
        await queryRunner.query(`CREATE TABLE "parameters" ("id" uuid NOT NULL DEFAULT uuid_generate_v4(), "name" character varying NOT NULL, "cwlType" character varying NOT NULL, "defaultValue" character varying, "description" character varying, "direction" "public"."parameters_direction_enum" NOT NULL DEFAULT 'input', "componentId" uuid, CONSTRAINT "PK_6b03a26baa3161f87fa87588859" PRIMARY KEY ("id"))`);
        await queryRunner.query(`ALTER TABLE "parameters" ADD CONSTRAINT "FK_e5d83de1b943d58a6a4900462c2" FOREIGN KEY ("componentId") REFERENCES "components"("id") ON DELETE CASCADE ON UPDATE NO ACTION`);
        await queryRunner.query(`CREATE TABLE "users" ("id" uuid NOT NULL DEFAULT uuid_generate_v4(), "email" character varying NOT NULL, "firstName" character varying, "lastName" character varying, "passwordHash" character varying NOT NULL, "createdAt" TIMESTAMP NOT NULL DEFAULT now(), CONSTRAINT "UQ_97672ac88f789774dd47f7c8be3" UNIQUE ("email"), CONSTRAINT "PK_a3ffb1c0c8416b9fc6f907b7433" PRIMARY KEY ("id"))`);
        await queryRunner.query(`ALTER TABLE "components" ADD CONSTRAINT "FK_f4d7a4e0e136b46c4593cd78869" FOREIGN KEY ("created_by_id") REFERENCES "users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION`);
    }

    public async down(queryRunner: QueryRunner): Promise<void> {
        await queryRunner.query(`ALTER TABLE "components" DROP CONSTRAINT "FK_f4d7a4e0e136b46c4593cd78869"`);
        await queryRunner.query(`DROP TABLE "users"`);
        await queryRunner.query(`ALTER TABLE "parameters" DROP CONSTRAINT "FK_e5d83de1b943d58a6a4900462c2"`);
        await queryRunner.query(`DROP TABLE "parameters"`);
        await queryRunner.query(`DROP TYPE "public"."parameters_direction_enum"`);
        await queryRunner.query(`DROP INDEX "public"."UQ_components_name_commitsha"`);
        await queryRunner.query(`DROP TABLE "components"`);
        await queryRunner.query(`DROP TYPE "public"."components_source_enum"`);
    }

}
