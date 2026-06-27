import {
  Body,
  Controller,
  Get,
  MaxFileSizeValidator,
  ParseFilePipe,
  Post,
  Query,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';

import { ComponentDomain } from './enums';
import { ComponentsService } from './components.service';
import { CreateComponentDto } from './dto/create-component.dto';
import { PackageComponentDto } from './dto/package-component.dto';

@Controller('components')
export class ComponentsController {
  constructor(private readonly componentsService: ComponentsService) {}

  @Get()
  async findAll(@Query('domain') domain?: ComponentDomain) {
    return this.componentsService.findAll(domain);
  }

  @Post()
  @UseInterceptors(FileInterceptor('cwlFile'))
  async create(
    @UploadedFile(
      new ParseFilePipe({
        validators: [new MaxFileSizeValidator({ maxSize: 1024 * 1024 })], // 1 MB
      }),
    )
    file: Express.Multer.File,
    @Body() dto: CreateComponentDto,
  ) {
    return this.componentsService.createManual(file, dto);
  }

  @Post('package')
  async package(@Body() dto: PackageComponentDto) {
    return this.componentsService.packageFromUrl(dto);
  }
}