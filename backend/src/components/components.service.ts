import * as fs from 'fs/promises';
import * as os from 'os';
import * as path from 'path';
import { spawn } from 'child_process';
import * as JSZip from 'jszip';

import {
  BadRequestException,
  ConflictException,
  ForbiddenException,
  Injectable,
  InternalServerErrorException,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { v4 as uuid } from 'uuid';

import { ComponentDomain, ComponentSource } from './enums';
import { CreateComponentDto } from './dto/create-component.dto';
import { UpdateComponentDto } from './dto/update-component.dto';
import { PackageComponentDto } from './dto/package-component.dto';
import { Component } from './entities/component.entity';
import { Parameter } from './entities/parameter.entity';
import { User } from '../users/entities/user.entity';
import { ComponentListItemDto } from './dto/component-list-item.dto';
import { ComponentDetailDto } from './dto/component-detail.dto';
import { ComponentTransformer } from './transformers/component.transformer';
import { CwlParser } from './cwl/cwl-parser';

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
    const components = domain
      ? await this.componentRepo.findBy({ domain })
      : await this.componentRepo.find();
    return components.map(ComponentTransformer.toListItem);
  }

  async findOne(id: string): Promise<ComponentDetailDto> {
    const component = await this.componentRepo.findOne({ where: { id }, relations: ['createdBy'] });
    if (!component) throw new NotFoundException(`Component ${id} not found`);
    return ComponentTransformer.toDetail(component);
  }

  async findVersions(id: string): Promise<ComponentListItemDto[]> {
    const component = await this.componentRepo.findOneBy({ id });
    if (!component) throw new NotFoundException(`Component ${id} not found`);
    const versions = await this.componentRepo.find({
      where: { name: component.name },
      order: { version: 'ASC' },
    });
    return versions.map(ComponentTransformer.toListItem);
  }

  async packageFromUrl(dto: PackageComponentDto, userId?: string): Promise<ComponentDetailDto> {
    const repoName = dto.repoUrl.split('/').at(-1)!;
    const tmpDir = path.join(os.tmpdir(), `moveapps-${uuid()}`);
    await fs.mkdir(tmpDir, { recursive: true });

    try {
      await this.runPackagingCli(dto.repoUrl, tmpDir);

      const cwlPath = path.join(tmpDir, `${repoName}.cwl`);
      const metadataPath = path.join(tmpDir, 'metadata.json');

      let cwlContent: string;
      let commitSha: string | null = null;
      let metadataDescription: string | null = null;
      let metadataAuthor: string | null = null;
      try {
        cwlContent = await fs.readFile(cwlPath, 'utf-8');
        const metadata = JSON.parse(await fs.readFile(metadataPath, 'utf-8'));
        commitSha = metadata.commitSha ?? null;
        metadataDescription = metadata.description ?? null;
        metadataAuthor = metadata.author ?? null;
      } catch {
        throw new InternalServerErrorException(
          'Packaging CLI exited successfully but expected output files are missing',
        );
      }

      const description = dto.description ?? metadataDescription;

      // Check if this repoUrl already exists in any lineage
      const existingInLineage = await this.componentRepo.findOne({
        where: { repoUrl: dto.repoUrl },
        relations: ['createdBy'],
      });

      if (existingInLineage) {
        this.ensureCreator(existingInLineage, userId);
        // Same commitSha -> already packaged, nothing to do
        if (commitSha && existingInLineage.repoCommitSha === commitSha) {
          throw new ConflictException(
            `Component '${repoName}' at commit ${commitSha} is already packaged`,
          );
        }
        // Different SHA -> create a new version in the same lineage
        return this.createNextVersion(existingInLineage, cwlContent, commitSha, description);
      }

      // New component: v1
      const parameters = this.parseParameters(cwlContent, 'CLI-generated');
      const component = this.componentRepo.create({
        name: repoName,
        authorName: metadataAuthor,
        createdBy: userId ? ({ id: userId } as User) : null,
        repoUrl: dto.repoUrl,
        repoCommitSha: commitSha,
        version: 1,
        cwlContent,
        description,
        source: ComponentSource.AUTOMATED_PACKAGING,
        domain: dto.domain,
        parameters: parameters as Parameter[],
      });

      this.logger.log(`Packaging complete: ${repoName} v1`);
      const saved = await this.componentRepo.save(component);
      return ComponentTransformer.toDetail(await this.reloadWithCreator(saved.id));
    } catch (err) {
      if (
        err instanceof ConflictException ||
        err instanceof ForbiddenException ||
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

  async addPackagedVersion(parentId: string, userId: string): Promise<ComponentDetailDto> {
    const parent = await this.componentRepo.findOne({ where: { id: parentId }, relations: ['createdBy'] });
    if (!parent) throw new NotFoundException(`Component ${parentId} not found`);
    this.ensureCreator(parent, userId);
    if (!parent.repoUrl) {
      throw new BadRequestException('Cannot repackage a manually uploaded component');
    }

    const latest = await this.componentRepo.findOne({
      where: { name: parent.name },
      order: { version: 'DESC' },
    });

    const repoName = parent.repoUrl.split('/').at(-1)!;
    const tmpDir = path.join(os.tmpdir(), `moveapps-${uuid()}`);
    await fs.mkdir(tmpDir, { recursive: true });

    try {
      await this.runPackagingCli(parent.repoUrl, tmpDir);

      const cwlPath = path.join(tmpDir, `${repoName}.cwl`);
      const metadataPath = path.join(tmpDir, 'metadata.json');

      let cwlContent: string;
      let commitSha: string | null = null;
      let metadataDescription: string | null = null;
      try {
        cwlContent = await fs.readFile(cwlPath, 'utf-8');
        const metadata = JSON.parse(await fs.readFile(metadataPath, 'utf-8'));
        commitSha = metadata.commitSha ?? null;
        metadataDescription = metadata.description ?? null;
      } catch {
        throw new InternalServerErrorException(
          'Packaging CLI exited successfully but expected output files are missing',
        );
      }

      if (commitSha && latest?.repoCommitSha === commitSha) {
        throw new ConflictException(
          `Component '${repoName}' at commit ${commitSha} is already packaged`,
        );
      }

      return this.createNextVersion(parent, cwlContent, commitSha, metadataDescription);
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

  async createManual(
    file: Express.Multer.File,
    dto: CreateComponentDto,
    userId?: string,
  ): Promise<ComponentDetailDto> {
    const cwlContent = file.buffer.toString('utf-8');
    const parameters = this.parseParameters(cwlContent, 'Uploaded');

    this.logger.log(`Manual upload: ${dto.name} v1`);

    const component = this.componentRepo.create({
      name: dto.name,
      authorName: dto.authorName ?? null,
      createdBy: userId ? ({ id: userId } as User) : null,
      repoUrl: dto.repoUrl || null,
      repoCommitSha: dto.repoCommitSha ?? null,
      version: 1,
      cwlContent,
      description: dto.description ?? CwlParser.extractDescription(cwlContent),
      source: ComponentSource.MANUAL_UPLOAD,
      domain: dto.domain,
      parameters: parameters as Parameter[],
    });

    const saved = await this.componentRepo.save(component);
    return ComponentTransformer.toDetail(await this.reloadWithCreator(saved.id));
  }

  async addManualVersion(
    parentId: string,
    file: Express.Multer.File,
    repoCommitSha: string | null,
    description: string | null,
    userId: string,
  ): Promise<ComponentDetailDto> {
    const parent = await this.componentRepo.findOne({ where: { id: parentId }, relations: ['createdBy'] });
    if (!parent) throw new NotFoundException(`Component ${parentId} not found`);
    this.ensureCreator(parent, userId);

    const cwlContent = file.buffer.toString('utf-8');
    return this.createNextVersion(parent, cwlContent, repoCommitSha, description ?? undefined);
  }

  async getCwlDownload(id: string): Promise<{ filename: string; content: string }> {
    const component = await this.componentRepo.findOneBy({ id });
    if (!component) throw new NotFoundException(`Component ${id} not found`);
    return {
      filename: `${component.name}-v${component.version}.cwl`,
      content: CwlParser.injectDescription(component.cwlContent, component.description),
    };
  }

  async getBundle(id: string): Promise<{ filename: string; buffer: Buffer }> {
    const component = await this.componentRepo.findOneBy({ id });
    if (!component) throw new NotFoundException(`Component ${id} not found`);

    const baseName = `${component.name}-v${component.version}`;
    const cwlContent = CwlParser.injectDescription(component.cwlContent, component.description);
    const inputsYaml = CwlParser.generateInputsYaml(component.parameters, component.name, component.version);

    const zip = new JSZip();
    zip.file(`${baseName}.cwl`, cwlContent);
    zip.file('inputs.yaml', inputsYaml);

    const buffer = await zip.generateAsync({ type: 'nodebuffer' });
    return { filename: `${baseName}.zip`, buffer };
  }

  async updateComponent(id: string, dto: UpdateComponentDto, userId: string): Promise<ComponentDetailDto> {
    const component = await this.componentRepo.findOne({ where: { id }, relations: ['createdBy'] });
    if (!component) throw new NotFoundException(`Component ${id} not found`);
    this.ensureCreator(component, userId);
    if (dto.description !== undefined) component.description = dto.description;
    if (dto.domain !== undefined) component.domain = dto.domain as ComponentDomain;
    const saved = await this.componentRepo.save(component);
    return ComponentTransformer.toDetail(saved);
  }

  async remove(id: string, userId: string): Promise<void> {
    const component = await this.componentRepo.findOne({ where: { id }, relations: ['createdBy'] });
    if (!component) throw new NotFoundException(`Component ${id} not found`);
    this.ensureCreator(component, userId);
    await this.componentRepo.delete(id);
  }

  // ── Private helpers ──────────────────────────────────────────────────────────

  private ensureCreator(component: Component, userId?: string): void {
    if (!userId || component.createdBy?.id !== userId) {
      throw new ForbiddenException('Only the creator of this component may perform this action');
    }
  }

  private async reloadWithCreator(id: string): Promise<Component> {
    return this.componentRepo.findOneOrFail({ where: { id }, relations: ['createdBy'] });
  }

  private async createNextVersion(
    parent: Component,
    cwlContent: string,
    commitSha: string | null,
    description: string | null = null,
  ): Promise<ComponentDetailDto> {
    const latest = await this.componentRepo.findOne({
      where: { name: parent.name },
      order: { version: 'DESC' },
    });
    const nextVersion = (latest?.version ?? 0) + 1;

    const parameters = this.parseParameters(cwlContent, `v${nextVersion}`);

    const component = this.componentRepo.create({
      name: parent.name,
      authorName: parent.authorName,
      createdBy: parent.createdBy,
      repoUrl: parent.repoUrl,
      repoCommitSha: commitSha,
      version: nextVersion,
      cwlContent,
      description: description ?? CwlParser.extractDescription(cwlContent),
      source: parent.source,
      domain: parent.domain,
      parameters: parameters as Parameter[],
    });

    this.logger.log(`New version: ${parent.name} v${nextVersion}`);
    const saved = await this.componentRepo.save(component);
    return ComponentTransformer.toDetail(await this.reloadWithCreator(saved.id));
  }

  private parseParameters(cwlContent: string, context: string): Partial<Parameter>[] {
    try {
      return CwlParser.extractParameters(cwlContent);
    } catch (err: any) {
      throw new BadRequestException(`${context} CWL could not be parsed: ${err.message}`);
    }
  }

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
}