import { Controller, Get } from '@nestjs/common';
import { ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import { VALID_DOMAINS } from '../components/enums';

@ApiTags('domains')
@Controller('domains')
export class DomainsController {
  @Get()
  @ApiOperation({ summary: 'List all available component domains' })
  @ApiResponse({ status: 200, type: [String] })
  list(): string[] {
    return VALID_DOMAINS;
  }
}