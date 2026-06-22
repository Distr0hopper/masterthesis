import { Body, Controller, Post, UploadedFile, UseInterceptors } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ComponentsService } from './components.service';
import { CreateComponentDto } from './dto/create-component.dto';
import { PackageComponentDto } from './dto/package-component.dto';

@Controller('components')
export class ComponentsController {
  constructor(private readonly componentsService: ComponentsService) {}

  // multipart/form-data: cwlFile field + JSON body fields
  @Post()
  @UseInterceptors(FileInterceptor('cwlFile'))
  async create(
    @UploadedFile() file: Express.Multer.File,
    @Body() dto: CreateComponentDto,
  ) {
    // implementation in Phase 3
  }

  @Post('package')
  async package(@Body() dto: PackageComponentDto) {
    // implementation in Phase 3
  }
}
