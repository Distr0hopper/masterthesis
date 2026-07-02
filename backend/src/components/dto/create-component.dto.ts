import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsEnum, IsOptional, IsString } from 'class-validator';
import { ComponentDomain } from '../enums';

export class CreateComponentDto {
  @ApiProperty({ example: 'My EO Component' })
  @IsString()
  name: string;

  @ApiProperty({ enum: ComponentDomain })
  @IsEnum(ComponentDomain)
  domain: ComponentDomain;
}
