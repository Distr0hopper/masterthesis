import * as fs from 'fs/promises';
import * as os from 'os';
import * as path from 'path';
import { spawn } from 'child_process';

import {
  BadRequestException,
  ConflictException,
  Injectable,
  InternalServerErrorException,
  Logger, NotFoundException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { InjectRepository } from '@nestjs/typeorm';
import * as yaml from 'js-yaml';
import { Repository } from 'typeorm';
import { v4 as uuid } from 'uuid';

import { ComponentDomain, ComponentSource, ParameterDirection } from './enums';
import { CreateComponentDto } from './dto/create-component.dto';
import { PackageComponentDto } from './dto/package-component.dto';
import { Component } from './entities/component.entity';
import { Parameter } from './entities/parameter.entity';
import {ComponentListItemDto} from "./dto/component-list-item.dto";
import {ComponentDetailDto} from "./dto/component-detail.dto";

@Injectable()
export class ComponentsService {
  private readonly logger = new Logger(ComponentsService.name);

  constructor(
    @InjectRepository(Component)
    private readonly componentRepo: Repository<Component>,
    @InjectRepository(Parameter)
    private readonly parameterRepo: Repository<Parameter>,
    private readonly configService: ConfigService,
  ) {}

  async findAll(domain?: ComponentDomain): Promise<ComponentListItemDto[]> {
    const components: ComponentListItemDto[] = domain
    ? await this.componentRepo.findBy( {domain} )
    : await this.componentRepo.find()

    return components.map((c) => ({
      id: c.id,
      name: c.name,
      repoUrl: c.repoUrl,
      domain: c.domain,
      source: c.source,
      createdAt: c.createdAt,
    }));
  }

  async findOne(id: string): Promise<ComponentDetailDto> {
    const component = await this.componentRepo.findOneBy({ id });
    if (!component) throw new NotFoundException(`Component ${id} not found`);
    return component;
  }

  async packageFromUrl(dto: PackageComponentDto): Promise<Component> {
    const existing = await this.componentRepo.findOne({ where: { repoUrl: dto.repoUrl } });
    if (existing) {
      throw new ConflictException(`Component with repoUrl '${dto.repoUrl}' already exists`);
    }

    const repoName = dto.repoUrl.split('/').at(-1)!;
    const tmpDir = path.join(os.tmpdir(), `moveapps-${uuid()}`);
    await fs.mkdir(tmpDir, { recursive: true });

    try {
      await this.runPackagingCli(dto.repoUrl, tmpDir);

      const cwlPath = path.join(tmpDir, `${repoName}.cwl`);
      const dockerfilePath = path.join(tmpDir, 'Dockerfile');

      let cwlContent: string;
      let dockerfileContent: string;
      try {
        [cwlContent, dockerfileContent] = await Promise.all([
          fs.readFile(cwlPath, 'utf-8'),
          fs.readFile(dockerfilePath, 'utf-8'),
        ]);
      } catch {
        throw new InternalServerErrorException(
          'Packaging CLI exited successfully but expected output files are missing',
        );
      }

      let parameters: Partial<Parameter>[];
      try {
        parameters = this.extractParameters(cwlContent);
      } catch (err: any) {
        throw new InternalServerErrorException(`CLI-generated CWL could not be parsed: ${err.message}`);
      }

      this.logger.log(`Packaging complete: ${repoName} (${parameters.length} parameters)`);

      const component = this.componentRepo.create({
        name: repoName,
        repoUrl: dto.repoUrl,
        repoCommitSha: null,
        cwlContent,
        dockerfileContent,
        source: ComponentSource.MOVEAPPS,
        domain: dto.domain,
        parameters: parameters as Parameter[],
      });

      return this.componentRepo.save(component);
    } catch (err) {
      if (
        err instanceof ConflictException ||
        err instanceof InternalServerErrorException ||
        err instanceof BadRequestException
      ) {
        throw err;
      }
      throw new BadRequestException((err as Error).message);
    } finally {
      await fs.rm(tmpDir, { recursive: true, force: true });
    }
  }

  async createManual(file: Express.Multer.File, dto: CreateComponentDto): Promise<Component> {
    const existing = await this.componentRepo.findOne({ where: { name: dto.name } });
    if (existing) {
      throw new ConflictException(`Component with name '${dto.name}' already exists`);
    }

    const cwlContent = file.buffer.toString('utf-8');

    let parameters: Partial<Parameter>[];
    try {
      parameters = this.extractParameters(cwlContent);
    } catch (err: any) {
      throw new BadRequestException(`Invalid CWL file: ${err.message}`);
    }

    this.logger.log(`Manual upload: ${dto.name} (${parameters.length} parameters)`);

    const component = this.componentRepo.create({
      name: dto.name,
      repoUrl: null,
      repoCommitSha: null,
      cwlContent,
      dockerfileContent: dto.dockerfileContent ?? '',
      source: ComponentSource.MANUAL,
      domain: dto.domain,
      parameters: parameters as Parameter[],
    });

    return this.componentRepo.save(component);
  }

  // ── Private helpers ─────────────────────────────────────────────────────────

  private async runPackagingCli(repoUrl: string, outputDir: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const executable = this.configService.get<string>('PACKAGING_EXECUTABLE')!;
      const githubToken = this.configService.get<string>('GITHUB_TOKEN');

      const args = [repoUrl, '--output-dir', outputDir];
      if (githubToken) args.push('--github-token', githubToken);

      this.logger.log(`Running: ${executable} ${args.join(' ')}`);

      const child = spawn(executable, args, { stdio: ['ignore', 'pipe', 'pipe'] });

      let stderr = '';
      child.stderr.on('data', (data: Buffer) => { stderr += data.toString(); });

      child.on('close', (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new BadRequestException(`Packaging CLI failed (exit ${code}): ${stderr.trim()}`));
        }
      });

      child.on('error', (err) => {
        reject(new InternalServerErrorException(`Failed to start packaging CLI: ${err.message}`));
      });
    });
  }

  private extractParameters(cwlContent: string): Partial<Parameter>[] {
    let doc: any;
    try {
      doc = yaml.load(cwlContent);
    } catch (err: any) {
      throw new Error(`YAML parse error: ${err.message}`);
    }

    const inputs: Record<string, any> = doc?.inputs ?? {};

    return Object.entries(inputs)
      .filter(([name]) => name !== 'input_rds')
      .map(([name, def]) => ({
        name,
        cwlType: String(def?.type ?? 'string').replace(/\?$/, ''),
        defaultValue: def?.default !== undefined ? String(def.default) : null,
        description: def?.doc ?? null,
        direction: ParameterDirection.INPUT,
      }));
  }
}
