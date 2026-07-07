import {
  Body,
  Controller, Delete,
  Get,
  MaxFileSizeValidator, Param,
  ParseFilePipe,
  Patch,
  Post,
  Query,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import {
  ApiBody,
  ApiConsumes,
  ApiExtraModels,
  ApiOperation, ApiParam,
  ApiQuery,
  ApiResponse,
  ApiTags,
  getSchemaPath,
} from '@nestjs/swagger';

import { ComponentDomain } from './enums';
import { ComponentsService } from './components.service';
import { CreateComponentDto } from './dto/create-component.dto';
import { PackageComponentDto } from './dto/package-component.dto';
import { UpdateComponentDto } from './dto/update-component.dto';
import {ComponentListItemDto} from "./dto/component-list-item.dto";
import {ComponentDetailDto} from "./dto/component-detail.dto";

@ApiTags('components')
@ApiExtraModels(CreateComponentDto)
@Controller('components')
export class ComponentsController {
  constructor(private readonly componentsService: ComponentsService) {}

  @Get()
  @ApiOperation({ summary: 'List all components' })
  @ApiQuery({ name: 'domain', enum: ComponentDomain, required: false })
  @ApiResponse({ status: 200, type: [ComponentListItemDto]})
  async findAll(@Query('domain') domain?: ComponentDomain) {
    return this.componentsService.findAll(domain);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Return component with ID' })
  @ApiParam({ name: 'id', required: true, description: 'Component ID' })
  @ApiResponse({ status: 200, description: 'Component found', type: ComponentDetailDto })
  @ApiResponse({ status: 404, description: 'Component not found' })
  async findOne(@Param('id') id: string) {
    return this.componentsService.findOne(id);
  }

  @Post()
  @UseInterceptors(FileInterceptor('cwlFile'))
  @ApiOperation({ summary: 'Manually upload a CWL file as a component' })
  @ApiConsumes('multipart/form-data')
  @ApiBody({
    schema: {
      allOf: [
        { $ref: getSchemaPath(CreateComponentDto) },
        {
          type: 'object',
          properties: {
            cwlFile: { type: 'string', format: 'binary' },
            name: { type: 'string' },
            domain: { type: 'string', enum: Object.values(ComponentDomain) },
          },
        },
      ],
    },
  })
  @ApiResponse({ status: 201, description: 'Component successfully created' })
  async create(
    @UploadedFile(
      new ParseFilePipe({
        validators: [new MaxFileSizeValidator({ maxSize: 1024 * 1024 })],
      }),
    )
    file: Express.Multer.File,
    @Body() dto: CreateComponentDto,
  ) {
    return this.componentsService.createManual(file, dto);
  }

  @Post('package')
  @ApiOperation({ summary: 'Package a MoveApps app from a GitHub repository URL' })
  @ApiResponse({ status: 201, description: 'Component successfully packaged and stored' })
  @ApiResponse({ status: 400, description: 'Invalid URL or packaging failed' })
  @ApiResponse({ status: 409, description: 'Component with this repoUrl already exists' })
  async package(@Body() dto: PackageComponentDto) {
    return this.componentsService.packageFromUrl(dto);
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Update the description of a component' })
  @ApiParam({ name: 'id', required: true, description: 'Component ID' })
  @ApiResponse({ status: 200, description: 'Description updated', type: ComponentDetailDto })
  @ApiResponse({ status: 404, description: 'Component not found' })
  async updateDescription(@Param('id') id: string, @Body() dto: UpdateComponentDto) {
    return this.componentsService.updateDescription(id, dto.description);
  }

  @Delete(':id')
    @ApiOperation({ summary: 'Delete a component by ID' })
    @ApiParam({ name: 'id', required: true, description: 'Component ID' })
    @ApiResponse({ status: 200, description: 'Component successfully deleted' })
    @ApiResponse({ status: 404, description: 'Component not found' })
    async remove(@Param('id') id: string): Promise<void> {
        return this.componentsService.remove(id);
    }
}