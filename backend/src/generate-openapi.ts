import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module';
import * as fs from 'fs';
import * as path from 'path';

async function generate() {
  const app = await NestFactory.create(AppModule, { logger: false });

  const config = new DocumentBuilder()
    .setTitle('Component Repository API')
    .setDescription('REST API for managing CWL-based workflow components')
    .setVersion('1.0')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  const outPath = path.resolve(__dirname, '../../openapi.json');
  fs.writeFileSync(outPath, JSON.stringify(document, null, 2));

  await app.close();
  console.log(`openapi.json written to ${outPath}`);
}

generate();