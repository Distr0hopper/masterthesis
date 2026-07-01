import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsUrl } from 'class-validator';
import { ComponentDomain } from '../enums';

export class PackageComponentDto {
  @ApiProperty({ example: 'https://github.com/movestore/Remove_Outliers' })
  @IsUrl()
  repoUrl: string;

  @ApiProperty({ enum: ComponentDomain })
  @IsEnum(ComponentDomain)
  domain: ComponentDomain;
}
